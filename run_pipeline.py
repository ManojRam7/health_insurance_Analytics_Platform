#!/usr/bin/env python
"""
Health Insurance – Full Pipeline Runner (with run reports)

Usage:
    python run_all_pipeline.py
    python run_all_pipeline.py --from-index 11
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import List, Dict, Any

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


# -----------------------------------------------------------------------------
# 1. Configure notebook list (ordered)
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[0]

NOTEBOOKS = [
    # 0. Pre-pilot / connectivity
    (
        "Pre-pilot – Spark & ADLS connectivity",
        PROJECT_ROOT 
        / "_00_Pre_Pilot" 
        / "Jupyter Notebooks"  
        / "01_spark_adls_connectors.ipynb",
    ),

    # 1. Bronze layer
    (
        "Bronze – data container & mounts",
        PROJECT_ROOT
        / "_01_Bronze" 
        / "Jupyter Notebooks"  
        / "00_bronze_data_connector.ipynb",
    ),
    (
        "Bronze – raw CSV → Delta",
        PROJECT_ROOT
        / "_01_Bronze" 
        / "Jupyter Notebooks"  
        / "01_data_load.ipynb",
    ),

    # 2. Silver layer
    (
        "Silver – Policies",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Policies" 
        / "01_policies_silver.ipynb",
    ),
    (
        "Silver – Members",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Members" 
        / "02_members_silver.ipynb",
    ),
    (
        "Silver – Claims",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Claims" 
        / "03_claims_silver.ipynb",
    ),
    (
        "Silver – Providers",
        PROJECT_ROOT
        / "_02_Silver" 
        / "Jupyter Notebooks" 
        / "Providers" 
        / "04_providers_silver.ipynb",
    ),

    # 3. Gold – fact tables
    (
        "Gold – fact_claims",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_01__fact_claims" 
        / "01_fact_claims.ipynb",
    ),
    (
        "Gold – fact_policies",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_02__fact_policies" 
        / "01_fact_policies.ipynb",
    ),
    (
        "Gold – fact_members",
        PROJECT_ROOT
       / "_03_Gold" 
       / "01_fact_dim_dm_star" 
       / "_03__fact_members" 
       / "01_fact_members.ipynb",
    ),

    # 4. Gold – dimensions
    (
        "Gold – dim tables (channel, product, region, member_segment)",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_04__dim_tables" 
        / "01_dim_tables.ipynb",
    ),
    (
        "Gold – dim_providers",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_04__dim_tables" 
        / "02_dim_providers.ipynb",
    ),

    # 5. Gold – data marts
    (
        "Gold – dm_policy_retention",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "01_dm_policy_retention.ipynb",
    ),
    (
        "Gold – dm_member_value",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "02_dm_member_value.ipynb",
    ),
    (
        "Gold – dm_claims_experience",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_05__data_marts" 
        / "03_dm_claims_experience.ipynb",
    ),

    # 6. Gold – star schemas
    (
        "Gold – star_claims",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "01_star_claims.ipynb",
    ),
    (
        "Gold – star_policies",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "02_star_policies.ipynb",
    ),
    (
        "Gold – star_members",
        PROJECT_ROOT
        / "_03_Gold" 
        / "01_fact_dim_dm_star" 
        / "_06__star_schemas" 
        / "03_star_members.ipynb",
    ),

    # 7. ML features
    (
        "ML Features – claim features",
        PROJECT_ROOT
        / "_03_Gold" 
        / "02_ML_Features" 
        / "01_claim_features.ipynb",
    ),
    (
        "ML Features – feature analysis",
        PROJECT_ROOT
        / "_03_Gold" 
        / "02_ML_Features"
        / "02_ML_Feature_Analysis.ipynb",
    ),

    # 8. ML model training
    (
        "ML – policy churn model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "01_policy_churn_prediction" 
        / "01_policy_churn_training.ipynb",
    ),
    (
        "ML – claims fraud model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "02_claims_risk_prediction"  
        / "01_Is_fraudulent_claim.ipynb",
    ),
    (
        "ML – high-cost claims model",
        PROJECT_ROOT
        / "_03_Gold" 
        / "03_ML_Model_Training" 
        / "02_claims_risk_prediction"  
        / "02_Is_high_cost_model.ipynb",
    ),

    # 9. Dashboards (SQL / views)
    (
        "Dashboards – Gold views",
        PROJECT_ROOT
        / "_03_Gold" 
        / "04_BI_Dashboards" 
        / "01_dashboard_views.ipynb",
    ),
    # 10. Data Quality monitoring 
    (
        
       "DQ Monitoring – central snapshot",
       PROJECT_ROOT
       / "_03_Gold"
       / "05_DQ_Monitoring"
       / "01_dq_monitoring.ipynb",
    
    ),
    
    
]

# -----------------------------------------------------------------------------
# 2. Helpers – notebook execution + report writing
# -----------------------------------------------------------------------------

def execute_notebook(nb_path: Path, kernel: str = "python") -> None:
    """Execute a single notebook in-place; raise if any cell fails."""
    with nb_path.open("r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=0, kernel_name=kernel)
    ep.preprocess(nb, {"metadata": {"path": str(nb_path.parent)}})

    # Optionally save executed notebook back (overwrites in-place)
    with nb_path.open("w", encoding="utf-8") as f:
        nbformat.write(nb, f)


def write_run_report(
    records: List[Dict[str, Any]],
    run_started_utc: dt.datetime,
    run_ended_utc: dt.datetime,
    from_index: int,
) -> None:
    """Persist a JSON + Markdown report for this pipeline run."""
    reports_dir = PROJECT_ROOT / "run_reports"
    reports_dir.mkdir(exist_ok=True)

    ts = run_started_utc.strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"run_report_{ts}.json"
    md_path = reports_dir / f"run_report_{ts}.md"

    # Derive summary stats
    total = len(records)
    success = sum(1 for r in records if r["status"] == "SUCCESS")
    failed = [r for r in records if r["status"] == "FAILED"]
    overall_status = "FAILED" if failed else "SUCCESS"

    meta = {
        "run_id": ts,
        "started_utc": run_started_utc.isoformat(),
        "finished_utc": run_ended_utc.isoformat(),
        "duration_seconds": (run_ended_utc - run_started_utc).total_seconds(),
        "from_index": from_index,
        "overall_status": overall_status,
        "total_notebooks": total,
        "success_count": success,
        "failed_count": len(failed),
    }

    payload = {"meta": meta, "notebooks": records}

    # --- JSON ----------------------------------------------------------------
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # --- Markdown ------------------------------------------------------------
    def fmt_sec(sec: float) -> str:
        return f"{sec:0.1f}s"

    longest = sorted(records, key=lambda r: r["duration_seconds"], reverse=True)[:3]

    lines: List[str] = []
    lines.append("# Health Insurance – Pipeline Run Report\n")
    lines.append(f"- **Run ID:** `{ts}`")
    lines.append(f"- **Status:** **{overall_status}**")
    lines.append(f"- **Started (UTC):** {meta['started_utc']}")
    lines.append(f"- **Finished (UTC):** {meta['finished_utc']}")
    lines.append(
        f"- **Duration:** {fmt_sec(meta['duration_seconds'])} "
        f"for {total} notebooks (from index {from_index})"
    )
    lines.append(
        f"- **Success:** {success}  |  **Failed:** {len(failed)}"
    )
    lines.append("\n---\n")

    lines.append("## Top 3 Longest Notebooks\n")
    if longest:
        for r in longest:
            lines.append(
                f"- `{r['index']:02d}` – `{r['name']}` → {fmt_sec(r['duration_seconds'])} "
                f"({r['status']})"
            )
    else:
        lines.append("- (no notebooks ran)")
    lines.append("\n---\n")

    lines.append("## Notebook Details\n")
    lines.append(
        "| Index | Notebook | Status | Duration | Started (UTC) | Finished (UTC) | Error (first line) |"
    )
    lines.append(
        "|------:|----------|--------|----------|---------------|----------------|--------------------|"
    )

    for r in records:
        err_first = ""
        if r["error"]:
            err_first = r["error"].splitlines()[0].replace("|", "¦")
        lines.append(
            f"| {r['index']:02d} "
            f"| `{r['name']}` "
            f"| {r['status']} "
            f"| {fmt_sec(r['duration_seconds'])} "
            f"| {r['started_utc']} "
            f"| {r['finished_utc']} "
            f"| {err_first} |"
        )

    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📄 Run report written to:")
    print(f"   JSON: {json_path}")
    print(f"   MD  : {md_path}\n")


# -----------------------------------------------------------------------------
# 3. Main – run all notebooks and record a report
# -----------------------------------------------------------------------------

def main(from_index: int) -> None:
    print("Health Insurance – Full Pipeline Run")
    print("=" * 70)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Total notebooks: {len(NOTEBOOKS)}")
    print(f"Starting from index: {from_index}\n")

    run_started_utc = dt.datetime.utcnow()
    records: List[Dict[str, Any]] = []

    for idx, (label, nb_path) in enumerate(NOTEBOOKS):
        rel_path = nb_path.relative_to(PROJECT_ROOT)
        display_name = f"{label} ({rel_path})"

        if idx < from_index:
            print(f"[{idx:02d}] SKIP  {display_name}")
            records.append(
                {
                    "index": idx,
                    "name": display_name,
                    "status": "SKIPPED",
                    "started_utc": None,
                    "finished_utc": None,
                    "duration_seconds": 0.0,
                    "error": None,
                }
            )
            continue

        print(f"[{idx:02d}] RUN   {display_name}")
        start_utc = dt.datetime.utcnow()
        t0 = time.perf_counter()
        status = "SUCCESS"
        err_text = None

        try:
            execute_notebook(nb_path)
        except Exception:
            status = "FAILED"
            err_text = traceback.format_exc()
            print(f"\n❌ Notebook FAILED: {display_name}")
            print("   (see error above)\n")
        finally:
            duration = time.perf_counter() - t0
            end_utc = dt.datetime.utcnow()

        records.append(
            {
                "index": idx,
                "name": display_name,
                "status": status,
                "started_utc": start_utc.isoformat(),
                "finished_utc": end_utc.isoformat(),
                "duration_seconds": duration,
                "error": err_text,
            }
        )

        if status == "FAILED":
            print("⚠️  Aborting pipeline after failure.")
            break

        print(f"   ✅ Completed in {duration:0.1f}s\n")

    run_ended_utc = dt.datetime.utcnow()
    write_run_report(records, run_started_utc, run_ended_utc, from_index)

    any_failed = any(r["status"] == "FAILED" for r in records)
    if any_failed:
        sys.exit(1)
    else:
        print("✅ Pipeline completed successfully.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-index",
        type=int,
        default=0,
        help="Start running notebooks from this index (0-based).",
    )
    args = parser.parse_args()
    main(from_index=args.from_index)
