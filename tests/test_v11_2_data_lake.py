import pytest
from aios_core.data_lake import DataLake

def test_encrypted_data_lake_export():
    lake = DataLake()
    
    lake.ingest({"user": "alice", "value": 1.0})
    lake.ingest({"user": "bob", "value": 2.5})
    
    result = lake.export_encrypted_pipeline(
        public_key="RSA_PUBLIC_KEY_MOCK_XYZ"
    )
    
    assert result["status"] == "success"
    assert result["records"] == 2
    assert "ENCRYPTED_BLOB" in result["encrypted_payload"]["ciphertext"]
    assert result["encrypted_payload"]["algorithm"] == "AES-256-GCM + RSA-4096"
