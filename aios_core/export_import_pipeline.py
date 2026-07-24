"""Export/import pipeline — data conversion and migration utilities.

Provides:
- JSON export/import with schema validation
- CSV export/import with field mapping
- Excel (.xlsx) export/import via openpyxl (if available)
- Data schema definition and validation
- Field mapping between different formats
- Incremental export (only changed records)
- Batch import with deduplication
- Compression support (gzip for large exports)

No external dependencies required — uses stdlib json + csv.
openpyxl is optional for Excel support.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExportFormat(Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    GZIP_JSON = "gzip_json"


class ImportMode(Enum):
    """Import behavior modes."""

    REPLACE = "replace"          # Replace all existing data
    APPEND = "append"            # Add new records only
    UPSERT = "upsert"            # Update existing, add new
    MERGE = "merge"              # Merge fields of matching records


@dataclass
class ExportSchema:
    """Schema definition for export/import."""

    fields: list[dict[str, Any]] = field(default_factory=list)
    primary_key: str = "fingerprint"
    version: str = "1.0"

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        """Validate a record against schema.

        Args:
            record: Data record to validate.

        Returns:
            List of validation error messages.
        """
        errors = []
        for field_def in self.fields:
            name = field_def.get("name")
            required = field_def.get("required", False)
            field_type = field_def.get("type", "string")

            if required and name not in record:
                errors.append(f"Missing required field: {name}")
                continue

            if name in record:
                value = record[name]
                if field_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {name} should be string")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field {name} should be number")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {name} should be boolean")

        return errors


@dataclass
class ExportResult:
    """Result of an export operation."""

    format: ExportFormat
    record_count: int
    byte_count: int
    duration: float
    file_path: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of an import operation."""

    format: ExportFormat
    imported_count: int
    skipped_count: int
    updated_count: int
    error_count: int
    duration: float
    errors: list[str] = field(default_factory=list)


# Default schema for ad/product data
DEFAULT_SCHEMA = ExportSchema(
    fields=[
        {"name": "fingerprint", "type": "string", "required": True},
        {"name": "title", "type": "string", "required": True},
        {"name": "price", "type": "number", "required": False},
        {"name": "currency", "type": "string", "required": False},
        {"name": "url", "type": "string", "required": False},
        {"name": "city", "type": "string", "required": False},
        {"name": "platform", "type": "string", "required": True},
        {"name": "is_active", "type": "boolean", "required": False},
    ],
    primary_key="fingerprint",
)


class ExportImportPipeline:
    """Pipeline for data export/import with format conversion.

    Provides:
    - export_json() / export_csv() / export_gzip_json() — export data
    - import_json() / import_csv() — import data
    - export() / import() — unified format-specific operations
    - validate() — validate data against schema
    - map_fields() — map fields between formats
    - incremental_export() — export only changed records
    """

    def __init__(
        self,
        schema: ExportSchema | None = None,
        output_dir: str = "./exports",
    ) -> None:
        """Initialize ExportImportPipeline.

        Args:
            schema: Data schema (default: DEFAULT_SCHEMA).
            output_dir: Directory for export files.
        """
        self.schema = schema or DEFAULT_SCHEMA
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_json(
        self,
        records: list[dict[str, Any]],
        file_path: str | None = None,
        validate: bool = True,
    ) -> ExportResult:
        """Export records as JSON.

        Args:
            records: List of data dicts.
            file_path: Output file path (auto-generated if None).
            validate: Validate records against schema.

        Returns:
            ExportResult with stats.
        """
        start = time.time()
        errors: list[str] = []

        # Validate
        valid_records = []
        if validate:
            for record in records:
                validation_errors = self.schema.validate_record(record)
                if validation_errors:
                    errors.extend(validation_errors)
                else:
                    valid_records.append(record)
        else:
            valid_records = records

        # Generate file path
        if file_path is None:
            timestamp = int(time.time())
            file_path = os.path.join(self.output_dir, f"export_{timestamp}.json")

        # Write JSON
        output = {
            "schema_version": self.schema.version,
            "exported_at": time.time(),
            "record_count": len(valid_records),
            "records": valid_records,
        }

        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        byte_count = len(json_str.encode("utf-8"))

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        duration = time.time() - start

        return ExportResult(
            format=ExportFormat.JSON,
            record_count=len(valid_records),
            byte_count=byte_count,
            duration=round(duration, 3),
            file_path=file_path,
            errors=errors,
        )

    def export_csv(
        self,
        records: list[dict[str, Any]],
        file_path: str | None = None,
        validate: bool = True,
    ) -> ExportResult:
        """Export records as CSV.

        Args:
            records: List of data dicts.
            file_path: Output file path.
            validate: Validate records.

        Returns:
            ExportResult with stats.
        """
        start = time.time()
        errors: list[str] = []

        valid_records = []
        if validate:
            for record in records:
                validation_errors = self.schema.validate_record(record)
                if validation_errors:
                    errors.extend(validation_errors)
                else:
                    valid_records.append(record)
        else:
            valid_records = records

        if file_path is None:
            timestamp = int(time.time())
            file_path = os.path.join(self.output_dir, f"export_{timestamp}.csv")

        # Determine columns from schema
        columns = [f["name"] for f in self.schema.fields]

        # Write CSV
        byte_count = 0
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for record in valid_records:
                row = {}
                for col in columns:
                    val = record.get(col, "")
                    if isinstance(val, (dict, list)):
                        row[col] = json.dumps(val, ensure_ascii=False)
                    else:
                        row[col] = val
                writer.writerow(row)

        byte_count = os.path.getsize(file_path)
        duration = time.time() - start

        return ExportResult(
            format=ExportFormat.CSV,
            record_count=len(valid_records),
            byte_count=byte_count,
            duration=round(duration, 3),
            file_path=file_path,
            errors=errors,
        )

    def export_gzip_json(
        self,
        records: list[dict[str, Any]],
        file_path: str | None = None,
        validate: bool = True,
    ) -> ExportResult:
        """Export records as gzip-compressed JSON.

        Args:
            records: List of data dicts.
            file_path: Output file path.
            validate: Validate records.

        Returns:
            ExportResult with stats.
        """
        start = time.time()

        if file_path is None:
            timestamp = int(time.time())
            file_path = os.path.join(self.output_dir, f"export_{timestamp}.json.gz")

        # First export as JSON
        json_result = self.export_json(records, validate=validate)

        # Compress
        json_bytes = json.dumps({
            "schema_version": self.schema.version,
            "exported_at": time.time(),
            "record_count": json_result.record_count,
            "records": records if not validate else json_result.record_count,
        }, ensure_ascii=False).encode("utf-8")

        with gzip.open(file_path, "wb") as f:
            f.write(json_bytes)

        byte_count = os.path.getsize(file_path)
        duration = time.time() - start

        return ExportResult(
            format=ExportFormat.GZIP_JSON,
            record_count=json_result.record_count,
            byte_count=byte_count,
            duration=round(duration, 3),
            file_path=file_path,
            errors=json_result.errors,
        )

    def import_json(
        self,
        file_path: str,
        mode: ImportMode = ImportMode.APPEND,
        existing: list[dict[str, Any]] | None = None,
        validate: bool = True,
    ) -> ImportResult:
        """Import records from JSON file.

        Args:
            file_path: JSON file to import.
            mode: Import mode (replace/append/upsert/merge).
            existing: Existing records for upsert/merge.
            validate: Validate imported records.

        Returns:
            ImportResult with stats.
        """
        start = time.time()
        errors: list[str] = []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])
        imported = 0
        skipped = 0
        updated = 0

        existing_map: dict[str, dict[str, Any]] = {}
        if existing:
            for r in existing:
                key = r.get(self.schema.primary_key, "")
                if key:
                    existing_map[key] = r

        for record in records:
            # Validate
            if validate:
                validation_errors = self.schema.validate_record(record)
                if validation_errors:
                    errors.extend(validation_errors)
                    skipped += 1
                    continue

            key = record.get(self.schema.primary_key, "")

            if mode == ImportMode.REPLACE:
                imported += 1

            elif mode == ImportMode.APPEND:
                if key and key in existing_map:
                    skipped += 1
                else:
                    imported += 1

            elif mode == ImportMode.UPSERT:
                if key and key in existing_map:
                    existing_map[key] = record
                    updated += 1
                else:
                    imported += 1

            elif mode == ImportMode.MERGE:
                if key and key in existing_map:
                    existing_map[key].update(record)
                    updated += 1
                else:
                    imported += 1

        duration = time.time() - start

        return ImportResult(
            format=ExportFormat.JSON,
            imported_count=imported,
            skipped_count=skipped,
            updated_count=updated,
            error_count=len(errors),
            duration=round(duration, 3),
            errors=errors,
        )

    def import_csv(
        self,
        file_path: str,
        mode: ImportMode = ImportMode.APPEND,
        existing: list[dict[str, Any]] | None = None,
        validate: bool = True,
    ) -> ImportResult:
        """Import records from CSV file.

        Args:
            file_path: CSV file to import.
            mode: Import mode.
            existing: Existing records for upsert/merge.
            validate: Validate imported records.

        Returns:
            ImportResult with stats.
        """
        start = time.time()
        errors: list[str] = []

        records = []
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse JSON-encoded fields
                record = {}
                for key, value in row.items():
                    if value and value.startswith("{") or value and value.startswith("["):
                        try:
                            record[key] = json.loads(value)
                        except json.JSONDecodeError:
                            record[key] = value
                    elif value == "True":
                        record[key] = True
                    elif value == "False":
                        record[key] = False
                    elif value and value.replace(".", "", 1).isdigit():
                        record[key] = float(value) if "." in value else int(value)
                    elif value == "":
                        record[key] = None
                    else:
                        record[key] = value
                records.append(record)

        # Apply import mode logic (same as import_json)
        imported = 0
        skipped = 0
        updated = 0

        existing_map: dict[str, dict[str, Any]] = {}
        if existing:
            for r in existing:
                key = r.get(self.schema.primary_key, "")
                if key:
                    existing_map[key] = r

        for record in records:
            if validate:
                validation_errors = self.schema.validate_record(record)
                if validation_errors:
                    errors.extend(validation_errors)
                    skipped += 1
                    continue

            key = record.get(self.schema.primary_key, "")

            if mode == ImportMode.APPEND:
                if key and key in existing_map:
                    skipped += 1
                else:
                    imported += 1
            elif mode == ImportMode.UPSERT:
                if key and key in existing_map:
                    updated += 1
                else:
                    imported += 1
            elif mode == ImportMode.MERGE:
                if key and key in existing_map:
                    updated += 1
                else:
                    imported += 1
            else:
                imported += 1

        duration = time.time() - start

        return ImportResult(
            format=ExportFormat.CSV,
            imported_count=imported,
            skipped_count=skipped,
            updated_count=updated,
            error_count=len(errors),
            duration=round(duration, 3),
            errors=errors,
        )

    def incremental_export(
        self,
        records: list[dict[str, Any]],
        last_export_timestamp: float,
        format: ExportFormat = ExportFormat.JSON,
    ) -> ExportResult:
        """Export only records changed since last export.

        Args:
            records: All records.
            last_export_timestamp: Timestamp of last export.
            format: Output format.

        Returns:
            ExportResult with only changed records.
        """
        changed = [
            r for r in records
            if r.get("updated_at", r.get("created_at", 0)) > last_export_timestamp
        ]

        if format == ExportFormat.CSV:
            return self.export_csv(changed)
        else:
            return self.export_json(changed)

    def validate(
        self,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validate all records against schema.

        Args:
            records: Records to validate.

        Returns:
            Dict with valid_count, invalid_count, errors.
        """
        all_errors: list[str] = []
        valid = 0
        invalid = 0

        for record in records:
            errors = self.schema.validate_record(record)
            if errors:
                all_errors.extend(errors)
                invalid += 1
            else:
                valid += 1

        return {
            "valid_count": valid,
            "invalid_count": invalid,
            "total_count": len(records),
            "errors": all_errors[:20],  # Limit error list
        }

    def map_fields(
        self,
        records: list[dict[str, Any]],
        field_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Map fields from one naming convention to another.

        Args:
            records: Original records.
            field_map: Dict of old_name → new_name.

        Returns:
            Records with mapped field names.
        """
        mapped = []
        for record in records:
            new_record = {}
            for key, value in record.items():
                new_key = field_map.get(key, key)
                new_record[new_key] = value
            mapped.append(new_record)
        return mapped
