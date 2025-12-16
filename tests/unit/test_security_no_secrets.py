
"""
from pathlib import Path
import re
import pytest

pytestmark = pytest.mark.unit

# Simple guardrails (not perfect, but effective).
PATTERNS = [
    (re.compile(r"client_secret\s*=\s*['\"].+['\"]", re.IGNORECASE), "Hardcoded client_secret"),
    (re.compile(r"fs\.azure\.account\.oauth2\.client\.secret", re.IGNORECASE), "Azure secret in spark.conf"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Possible AWS access key"),
]

SCAN_EXTS = {".py", ".ipynb", ".yml", ".yaml", ".txt", ".md"}

def test_no_obvious_secrets_in_repo():
    root = Path(".")
    bad = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.parts[0] in {".git", ".pytest_cache", "mlruns", "spark-warehouse"}:
            continue
        if p.suffix.lower() not in SCAN_EXTS:
            continue

        text = p.read_text(errors="ignore")
        for rx, msg in PATTERNS:
            if rx.search(text):
                bad.append(f"{p}: {msg}")

    assert not bad, "Potential secrets found:\n" + "\n".join(bad)


"""