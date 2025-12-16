"""Security test: Check for obvious hardcoded secrets in the repo."""
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
    """Scan repo for obvious hardcoded secrets."""
    root = Path(".")
    bad = []
    
    # Directories to skip (dev environments, dependencies, notebooks with legitimate config)
    skip_dirs = {
        ".git", ".pytest_cache", "mlruns", "spark-warehouse", 
        ".mlflow_venv", ".venv", "venv", "env",
        "node_modules", "__pycache__",
        # Notebooks often have example configs (not real secrets)
        "_00_Pre_Pilot", "Jupyter Notebooks", "Notebooks", "Data_Collection"
    }

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # Skip if any part of the path is in skip_dirs
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.suffix.lower() not in SCAN_EXTS:
            continue

        text = p.read_text(errors="ignore")
        for rx, msg in PATTERNS:
            if rx.search(text):
                bad.append(f"{p}: {msg}")

    assert not bad, "Potential secrets found:\n" + "\n".join(bad)