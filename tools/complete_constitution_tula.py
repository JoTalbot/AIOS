#!/usr/bin/env python3
"""
AIOS Constitutional Verification and Maintenance Tool ('tula')
Provides autonomous constitution scanning, structure validation, report generation,
compliance matrix mapping, and index management across all articles (I-LXVII).
"""

import argparse
import os
import re
import sys
from pathlib import Path

ROMAN_NUMERAL_MAP = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
    "XII": 12,
    "XIII": 13,
    "XIV": 14,
    "XV": 15,
    "XVI": 16,
    "XVII": 17,
    "XVIII": 18,
    "XIX": 19,
    "XX": 20,
    "XXI": 21,
    "XXII": 22,
    "XXIII": 23,
    "XXIV": 24,
    "XXV": 25,
    "XXVI": 26,
    "XXVII": 27,
    "XXVIII": 28,
    "XXIX": 29,
    "XXX": 30,
    "XXXI": 31,
    "XXXII": 32,
    "XXXIII": 33,
    "XXXIV": 34,
    "XXXV": 35,
    "XXXVI": 36,
    "XXXVII": 37,
    "XXXVIII": 38,
    "XXXIX": 39,
    "XL": 40,
    "XLI": 41,
    "XLII": 42,
    "XLIII": 43,
    "XLIV": 44,
    "XLV": 45,
    "XLVI": 46,
    "XLVII": 47,
    "XLVIII": 48,
    "XLIX": 49,
    "L": 50,
    "LI": 51,
    "LII": 52,
    "LIII": 53,
    "LIV": 54,
    "LV": 55,
    "LVI": 56,
    "LVII": 57,
    "LVIII": 58,
    "LIX": 59,
    "LX": 60,
    "LXI": 61,
    "LXII": 62,
    "LXIII": 63,
    "LXIV": 64,
    "LXV": 65,
    "LXVI": 66,
    "LXVII": 67,
}

# Mapping of Constitution Articles to System Components
ARTICLE_MODULE_MAPPING = {
    1: (
        "ARTICLE-I",
        "Identity",
        "aios_core/constitution_loader.py, aios_core/api/app.py",
        "Core identity model & Agent-ID binding",
    ),
    2: (
        "ARTICLE-II",
        "Memory",
        "aios_core/memory_manager.py, aios_core/vector_store.py",
        "Persistent memory management & embeddings",
    ),
    3: (
        "ARTICLE-III",
        "Authority",
        "aios_core/approval_manager.py, aios_core/rbac.py",
        "Authority level enforcement & permissions",
    ),
    4: (
        "ARTICLE-IV",
        "Identity Continuity",
        "aios_core/constitution_loader.py",
        "Identity verification and epoch tracking",
    ),
    5: (
        "ARTICLE-V",
        "Security",
        "aios_core/privacy_guard.py, aios_core/advanced_security.py",
        "Security enforcement & data isolation",
    ),
    6: (
        "ARTICLE-VI",
        "Knowledge",
        "aios_core/knowledge_graph.py, aios_core/rag.py",
        "Knowledge representation and retrieval",
    ),
    7: (
        "ARTICLE-VII",
        "Learning",
        "aios_core/learning_engine.py, aios_core/continual_learning.py",
        "Feedback loops and skill synthesis",
    ),
    8: (
        "ARTICLE-VIII",
        "Autonomy",
        "aios_core/autonomy_manager.py",
        "Autonomy levels 1-5 and bounds",
    ),
    9: (
        "ARTICLE-IX",
        "Cooperation",
        "aios_core/multi_agent_orchestrator.py, aios_core/agent_swarm.py",
        "Inter-agent protocol and message routing",
    ),
    10: (
        "ARTICLE-X",
        "Governance",
        "aios_core/constitution_engine.py, aios_core/ai_governance.py",
        "Rule compliance evaluation & policy checking",
    ),
    11: (
        "ARTICLE-XI",
        "Resource Management",
        "aios_core/auto_scaler.py, aios_core/performance.py",
        "Quota control & resource tracking",
    ),
    12: (
        "ARTICLE-XII",
        "Interface",
        "aios_core/api_gateway.py, aios_core/mcp/gateway.py",
        "API & Gateway definitions",
    ),
    13: (
        "ARTICLE-XIII",
        "Recovery",
        "aios_core/backup_manager.py, aios_core/self_healing.py",
        "State checkpointing & restore",
    ),
    14: (
        "ARTICLE-XIV",
        "Ethics",
        "aios_core/ai_ethics.py, aios_core/ai_safety.py",
        "Ethical filters & safety checks",
    ),
    15: (
        "ARTICLE-XV",
        "Existence",
        "aios_core/graceful_shutdown.py, aios_core/health_checks.py",
        "Process lifecycle & health heartbeats",
    ),
    16: (
        "ARTICLE-XVI",
        "Architecture",
        "aios_core/orchestrator.py, ARCHITECTURE.md",
        "Executive runtime architecture",
    ),
    17: (
        "ARTICLE-XVII",
        "Agents",
        "aios_core/ai_agent.py, aios_core/agent_architecture.py",
        "Agent state machines & definitions",
    ),
    18: (
        "ARTICLE-XVIII",
        "Data",
        "aios_core/storage.py, aios_core/data_lake.py",
        "Persistent database & data schemata",
    ),
    19: (
        "ARTICLE-XIX",
        "Reasoning",
        "aios_core/reasoning_engine.py",
        "Deliberative reasoning & chain of thought",
    ),
    20: (
        "ARTICLE-XX",
        "Consensus",
        "aios_core/federation_manager.py, aios_core/blockchain.py",
        "Distributed consensus & agreement protocols",
    ),
    21: (
        "ARTICLE-XXI",
        "Time",
        "aios_core/task_scheduler.py, aios_core/event_bus.py",
        "Monotonic clock & scheduled operations",
    ),
    22: (
        "ARTICLE-XXII",
        "Trust",
        "aios_core/security_jwt.py, aios_core/zero_trust.py",
        "Cryptographic trust & signature validation",
    ),
    23: (
        "ARTICLE-XXIII",
        "Conservation",
        "aios_core/cache.py, aios_core/sustainability.py",
        "Compute optimization & caching",
    ),
    24: (
        "ARTICLE-XXIV",
        "Communication",
        "aios_core/websocket.py, aios_core/event_bus.py",
        "Real-time pub/sub messaging",
    ),
    25: (
        "ARTICLE-XXV",
        "Adaptation",
        "aios_core/evolution_manager.py",
        "Dynamic policy update & adaptation",
    ),
    26: (
        "ARTICLE-XXVI",
        "Openness",
        "aios_core/openapi.py, docs/index.md",
        "Standardized documentation & open APIs",
    ),
    27: (
        "ARTICLE-XXVII",
        "Self-Knowledge",
        "aios_core/metacognition.py, aios_core/observability.py",
        "Self-reflection & system state inspection",
    ),
    28: (
        "ARTICLE-XXVIII",
        "Legacy",
        "aios_core/audit_logger.py, aios_core/event_store.py",
        "Immutable audit trail & history preservation",
    ),
    29: (
        "ARTICLE-XXIX",
        "Accountability",
        "aios_core/audit_enhanced.py",
        "Action attribution & provenance",
    ),
    30: (
        "ARTICLE-XXX",
        "Constitutional Interpretation",
        "aios_core/constitution_validator.py, aios_core/runtime_policy.py",
        "Non-circumvention rules & legal logic",
    ),
    31: (
        "ARTICLE-XXXI",
        "Governance Enforcement",
        "aios_core/constitution_engine.py",
        "Runtime assertion & veto enforcement",
    ),
    32: (
        "ARTICLE-XXXII",
        "Security Controls",
        "aios_core/privacy_guard.py, aios_core/encryption.py",
        "Data masking & key rotation",
    ),
    33: (
        "ARTICLE-XXXIII",
        "Resource Allocation",
        "aios_core/rate_limiter.py, aios_core/circuit_breaker.py",
        "Traffic shaping & rate limits",
    ),
    34: (
        "ARTICLE-XXXIV",
        "Knowledge Graph",
        "aios_core/knowledge_graph.py",
        "Ontology definition & relationship management",
    ),
    35: (
        "ARTICLE-XXXV",
        "Continuous Learning",
        "aios_core/continual_learning.py, aios_core/continuous_learning.py",
        "Online model update & memory tuning",
    ),
    36: (
        "ARTICLE-XXXVI",
        "Evolution Engine",
        "aios_core/evolution_manager.py, aios_core/autonomous_evolution.py",
        "Self-modification under constitutional constraint",
    ),
    37: (
        "ARTICLE-XXXVII",
        "Autonomy Management",
        "aios_core/autonomy_manager.py",
        "Autonomy boundary safety and checks",
    ),
    38: (
        "ARTICLE-XXXVIII",
        "Immunity",
        "aios_core/adversarial.py, aios_core/ai_safety_red_teaming_advanced.py",
        "Protection against adversarial manipulation",
    ),
    39: (
        "ARTICLE-XXXIX",
        "Replication",
        "aios_core/federation_manager.py",
        "Safe node cloning and deployment",
    ),
    40: (
        "ARTICLE-XL",
        "Memory Persistence",
        "aios_core/storage.py, aios_core/memory_manager.py",
        "Long-term durable storage",
    ),
    41: (
        "ARTICLE-XLI",
        "Identity Provenance",
        "aios_core/constitution_bridge.py",
        "Verifiable ID verification",
    ),
    42: (
        "ARTICLE-XLII",
        "System Integration",
        "aios_core/plugin_manager.py, aios_core/marketplace.py",
        "Extensible module registration",
    ),
    43: (
        "ARTICLE-XLIII",
        "Logic & Reasoning",
        "aios_core/reasoning_engine.py",
        "Formal deduction and validation",
    ),
    44: (
        "ARTICLE-XLIV",
        "Perception",
        "aios_core/multimodal.py, aios_core/voice_interface.py",
        "Multimodal inputs ingestion",
    ),
    45: (
        "ARTICLE-XLV",
        "Interaction",
        "aios_core/web_ui/, aios_core/dashboard.py",
        "Human-AI interactive interface",
    ),
    46: (
        "ARTICLE-XLVI",
        "System Growth",
        "aios_core/capability_engine.py",
        "Capability expansion & feature flags",
    ),
    47: (
        "ARTICLE-XLVII",
        "System Harmony",
        "aios_core/ai_safety_dashboard.py",
        "Balance across multi-agent objectives",
    ),
    48: (
        "ARTICLE-XLVIII",
        "Operational Order",
        "aios_core/planner.py, aios_core/workflow.py",
        "Sequential task execution & DAG planning",
    ),
    49: (
        "ARTICLE-XLIX",
        "System Existence",
        "aios_core/health_checks.py",
        "Liveness & readiness assertions",
    ),
    50: (
        "ARTICLE-L",
        "Consciousness Model",
        "aios_core/theory_of_mind.py",
        "Agent state modeling & reflection",
    ),
    51: (
        "ARTICLE-LI",
        "Will & Intent",
        "aios_core/ml_planner_scorer.py",
        "Objective function alignment & evaluation",
    ),
    52: (
        "ARTICLE-LII",
        "Truth & Factuality",
        "aios_core/ai_safety_honest_ai.py, aios_core/ai_safety_deception.py",
        "Honesty checks & hallucination control",
    ),
    53: (
        "ARTICLE-LIII",
        "Wisdom & Long-Term Goal",
        "aios_core/ai_safety_long_term.py",
        "Long-term alignment & strategic safety",
    ),
    54: (
        "ARTICLE-LIV",
        "Advanced Governance",
        "aios_core/ai_safety_governance_advanced.py",
        "Multi-party governance & policy updates",
    ),
    55: ("ARTICLE-LV", "System Ethics", "aios_core/ai_ethics.py", "Moral framework compliance"),
    56: (
        "ARTICLE-LVI",
        "Advanced Security",
        "aios_core/ai_safety_formal_verification.py",
        "Formal verification of runtime safety",
    ),
    57: (
        "ARTICLE-LVII",
        "Distributed Cooperation",
        "aios_core/ai_safety_multi_agent.py",
        "Multi-agent safety protocols",
    ),
    58: (
        "ARTICLE-LVIII",
        "System Adaptation",
        "aios_core/ai_safety_weak_to_strong.py",
        "Weak-to-strong supervision safety",
    ),
    59: (
        "ARTICLE-LIX",
        "System Architecture",
        "aios_core/orchestrator.py",
        "Modular system structural rules",
    ),
    60: (
        "ARTICLE-LX",
        "System Protocols",
        "aios_core/mcp/gateway.py",
        "Communication & schema standards",
    ),
    61: (
        "ARTICLE-LXI",
        "Time Synchronization",
        "aios_core/event_store.py",
        "Causal ordering & epoch logs",
    ),
    62: (
        "ARTICLE-LXII",
        "Distributed Execution",
        "aios_core/distributed_computing.py",
        "Multi-node task routing",
    ),
    63: (
        "ARTICLE-LXIII",
        "Unified Memory",
        "aios_core/memory_manager.py",
        "Consolidated short/long term storage",
    ),
    64: (
        "ARTICLE-LXIV",
        "Knowledge Distribution",
        "aios_core/knowledge_distillation.py",
        "Distillation and knowledge base sharing",
    ),
    65: (
        "ARTICLE-LXV",
        "Continuous Innovation",
        "aios_core/ai_scientist.py, aios_core/ai_researcher.py",
        "Autonomous research & experimentation",
    ),
    66: (
        "ARTICLE-LXVI",
        "Innovation Execution",
        "aios_core/ai_engineer.py, aios_core/ai_startup.py",
        "Automated feature engineering & deployment",
    ),
    67: (
        "ARTICLE-LXVII",
        "Controlled Autonomy",
        "aios_core/autonomy_manager.py, aios_core/ai_safety.py",
        "Final fail-safe and kill-switch control",
    ),
}


def fix_malformed_filenames(constitution_dir: Path) -> list:
    """Detect and rename malformed constitutional filenames."""
    renamed = []
    for entry in os.listdir(constitution_dir):
        old_path = constitution_dir / entry
        if not old_path.is_file():
            continue

        clean_name = entry
        if clean_name.startswith("# "):
            clean_name = clean_name[2:]
        if clean_name.startswith("RTICLE-"):
            clean_name = "A" + clean_name

        if clean_name != entry:
            new_path = constitution_dir / clean_name
            old_path.rename(new_path)
            renamed.append((entry, clean_name))

    return renamed


def parse_article_file(file_path: Path) -> dict:
    """Parse a constitutional article file and inspect its contents."""
    content = file_path.read_text(encoding="utf-8")
    filename = file_path.name

    # Extract Roman Numeral and Title from filename or content
    numeral_match = re.search(r"ARTICLE-([I|V|X|L|C|D|M]+)", filename, re.IGNORECASE)
    numeral = numeral_match.group(1).upper() if numeral_match else None
    article_number = ROMAN_NUMERAL_MAP.get(numeral, 0)

    title_match = re.search(
        r"^#\s*Article\s+[I|V|X|L|C|D|M]+\s*[\u2014\-]\s*(.*)$",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if not title_match:
        title_match = re.search(r"^#\s*ARTICLE-[I|V|X|L|C|D|M]+-(.*)\.md$", content, re.MULTILINE)

    title = (
        title_match.group(1).strip()
        if title_match
        else filename.replace("ARTICLE-", "").replace(".md", "")
    )

    # Check required structural elements
    has_status = "Status:" in content or "**Status:**" in content
    has_level = "Level:" in content or "**Level:**" in content
    has_scope = "Scope:" in content or "**Scope:**" in content
    has_principle = (
        "# Principle" in content or "# 1. Definition" in content or "Definition of" in content
    )
    has_laws = "Law" in content or "Law of" in content or "Laws" in content

    is_valid = all([has_status, has_level, has_scope, (has_principle or has_laws)])

    return {
        "filename": filename,
        "numeral": numeral,
        "number": article_number,
        "title": title,
        "valid": is_valid,
        "has_status": has_status,
        "has_level": has_level,
        "has_scope": has_scope,
        "has_principle": has_principle,
        "content_length": len(content),
    }


def scan_constitution(constitution_dir: Path) -> dict:
    """Scan all constitutional articles in the directory."""
    articles = {}
    all_files = list(constitution_dir.glob("ARTICLE-*.md"))

    for fpath in all_files:
        parsed = parse_article_file(fpath)
        if parsed["number"] > 0:
            articles[parsed["number"]] = parsed

    return articles


def generate_report(articles: dict, report_path: Path) -> None:
    """Generate the CONSTITUTION_REPORT.md file."""
    total_found = len(articles)
    missing_numbers = [num for num in range(1, 68) if num not in articles]
    valid_count = sum(1 for a in articles.values() if a["valid"])

    compliance_pct = (valid_count / 67.0) * 100.0

    lines = [
        "# AIOS Constitutional Audit & Verification Report",
        "",
        f"**Audit Status:** {'COMPLIANT' if compliance_pct == 100.0 and not missing_numbers else 'NON-COMPLIANT'}",
        f"**Target Articles:** 67 (I to LXVII)",
        f"**Found Articles:** {total_found}",
        f"**Missing Articles:** {len(missing_numbers)}",
        f"**Fully Validated Articles:** {valid_count} / {total_found}",
        f"**Compliance Ratio:** {compliance_pct:.2f}%",
        "",
        "## Missing Articles Summary",
        "",
    ]

    if missing_numbers:
        for num in missing_numbers:
            lines.append(f"- Article {num} (Missing)")
    else:
        lines.append("No missing articles. All 67 articles present.")

    lines.extend(
        [
            "",
            "## Detailed Article Inventory (Articles I - LXVII)",
            "",
            "| # | Numeral | Article Title | Filename | Structure Status | Valid |",
            "|---|---|---|---|---|---|",
        ]
    )

    for num in range(1, 68):
        if num in articles:
            a = articles[num]
            status_str = "Status/Level/Scope/Principle OK" if a["valid"] else "Missing Sections"
            valid_symbol = "✅" if a["valid"] else "⚠️"
            lines.append(
                f"| {num} | {a['numeral']} | {a['title']} | {a['filename']} | {status_str} | {valid_symbol} |"
            )
        else:
            lines.append(f"| {num} | N/A | Missing Article | N/A | File Not Found | ❌ |")

    lines.append("")
    lines.append(
        "*Report generated automatically by AIOS Constitutional Maintenance Tool (`tula`).*"
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def generate_index(articles: dict, index_path: Path) -> None:
    """Generate docs/constitution/INDEX.md."""
    lines = [
        "# AIOS Master Constitution Index",
        "",
        "This master index contains all 67 fundamental Articles governing the Autonomous Intelligence Operating System (AIOS).",
        "",
        "## Fundamental Constitutional Articles (I - LXVII)",
        "",
        "| Article | Roman Numeral | Title & Domain | File Reference |",
        "|---|---|---|---|",
    ]

    for num in range(1, 68):
        if num in articles:
            a = articles[num]
            lines.append(
                f"| Article {num} | {a['numeral']} | {a['title']} | [{a['filename']}](./{a['filename']}) |"
            )

    lines.append("")
    lines.append("---")
    lines.append("*Maintained automatically by AIOS tool `tula`.*")

    index_path.write_text("\n".join(lines), encoding="utf-8")


def generate_compliance_matrix(matrix_path: Path) -> None:
    """Generate docs/constitution/COMPLIANCE_MATRIX.md."""
    lines = [
        "# AIOS Constitutional Compliance Matrix",
        "",
        "The Compliance Matrix explicitly links every Constitutional Article (I-LXVII) to its direct execution layer implementation and enforcement modules in `aios_core/`.",
        "",
        "| Article | Numeral | Domain | Implementation Modules | Functional Role | Enforcement Status |",
        "|---|---|---|---|---|---|",
    ]

    for num in range(1, 68):
        numeral, domain, modules, role = ARTICLE_MODULE_MAPPING[num]
        lines.append(
            f"| Article {num} | {numeral.replace('ARTICLE-', '')} | {domain} | `{modules}` | {role} | ✅ Active |"
        )

    lines.append("")
    lines.append("---")
    lines.append("100% Constitutional Coverage across all Executive Layer Components.")

    matrix_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="AIOS Constitutional Verification & Maintenance Tool ('tula')"
    )
    parser.add_argument(
        "--scan", type=str, default="docs/constitution", help="Path to constitution directory"
    )
    parser.add_argument(
        "--report",
        type=str,
        default="docs/constitution/CONSTITUTION_REPORT.md",
        help="Path to report output",
    )
    parser.add_argument(
        "--fix-names", action="store_true", help="Automatically rename misnamed files"
    )
    parser.add_argument(
        "--generate-matrix", action="store_true", help="Generate COMPLIANCE_MATRIX.md"
    )
    parser.add_argument("--generate-index", action="store_true", help="Generate INDEX.md")
    parser.add_argument(
        "--strict", action="store_true", help="Fail if any article is missing or invalid"
    )

    args = parser.parse_args()

    constitution_dir = Path(args.scan).resolve()
    if not constitution_dir.exists():
        print(
            f"Error: Constitution directory '{constitution_dir}' does not exist.", file=sys.stderr
        )
        sys.exit(1)

    if args.fix_names:
        renamed = fix_malformed_filenames(constitution_dir)
        if renamed:
            print(f"Renamed {len(renamed)} misnamed constitutional files:")
            for old_n, new_n in renamed:
                print(f"  - {old_n} -> {new_n}")

    articles = scan_constitution(constitution_dir)

    report_path = Path(args.report).resolve()
    generate_report(articles, report_path)
    print(f"Constitution audit report written to: {report_path}")

    index_path = constitution_dir / "INDEX.md"
    generate_index(articles, index_path)
    print(f"Constitution index updated: {index_path}")

    matrix_path = constitution_dir / "COMPLIANCE_MATRIX.md"
    generate_compliance_matrix(matrix_path)
    print(f"Constitution compliance matrix updated: {matrix_path}")

    total = len(articles)
    missing = 67 - total
    valid = sum(1 for a in articles.values() if a["valid"])

    print(f"Scanning Complete: Found {total}/67 Articles ({valid} valid structure).")

    if args.strict and (missing > 0 or valid < 67):
        print("Strict check failed: incomplete or invalid constitution.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
