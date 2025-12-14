from __future__ import annotations

from pathlib import Path
import argparse
import mlflow
from mlflow.tracking import MlflowClient

PROJECT_ROOT = Path("/Users/manojrammopati/Public/Projects/health_insurance_project")
TRACKING_URI = f"file:{PROJECT_ROOT / 'mlruns'}"
mlflow.set_tracking_uri(TRACKING_URI)

client = MlflowClient()

CONFIG = [
    # (experiment_name, registered_model_name, artifact_path_logged_in_notebook)
    ("health_policy_churn",      "health_policy_churn_model",   "best_policy_churn_model"),
    ("health_fraud_claim",       "health_claims_fraud_model",   "fraud_best_model"),
    ("health_claims_high_cost",  "health_high_cost_model",      "high_cost_best_model"),
]


def latest_finished_run_id(experiment_name: str) -> str:
    exp = client.get_experiment_by_name(experiment_name)
    if exp is None:
        raise RuntimeError(f"Experiment not found: {experiment_name}")

    df = mlflow.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    if df is None or len(df) == 0:
        raise RuntimeError(f"No FINISHED runs found for experiment: {experiment_name}")

    return str(df.loc[0, "run_id"])


def ensure_registered_model(name: str):
    try:
        client.create_registered_model(name)
        print(f"✅ Created registered model: {name}")
    except Exception:
        # already exists
        pass


def get_version_for_run(model_name: str, run_id: str) -> str | None:
    versions = client.search_model_versions(f"name='{model_name}'")
    for v in versions:
        if getattr(v, "run_id", None) == run_id:
            return str(v.version)
    return None


def register_latest_if_needed(experiment_name: str, model_name: str, artifact_path: str) -> str:
    run_id = latest_finished_run_id(experiment_name)
    model_uri = f"runs:/{run_id}/{artifact_path}"

    ensure_registered_model(model_name)

    existing_ver = get_version_for_run(model_name, run_id)
    if existing_ver is not None:
        print(f"⚠️ Already registered: {model_name} v{existing_ver} for run_id={run_id}")
        return existing_ver

    mv = client.create_model_version(
        name=model_name,
        source=model_uri,
        run_id=run_id,
    )
    print(f"✅ Registered {model_name} v{mv.version} from run_id={run_id}")
    return str(mv.version)


def promote_alias(model_name: str, version: str, alias: str, *, tags: dict[str, str] | None = None):
    client.set_registered_model_alias(model_name, alias, version)
    print(f"✅ Set alias '{alias}' -> {model_name} v{version}")

    # Add audit tags at version level
    client.set_model_version_tag(model_name, version, "lifecycle_alias", alias)
    if tags:
        for k, v in tags.items():
            client.set_model_version_tag(model_name, version, str(k), str(v))


def list_aliases(model_name: str):
    rm = client.get_registered_model(model_name)
    aliases = getattr(rm, "aliases", None)  # MLflow returns a dict-like in recent versions
    print(f"Aliases for {model_name}: {aliases}")


def main():
    parser = argparse.ArgumentParser(description="Register latest models and promote to MLflow aliases.")
    parser.add_argument("--alias", default="staging", help="Alias to set (e.g., staging, prod, uat, dev)")
    parser.add_argument("--also-prod", action="store_true", help="Also set alias 'prod' to the same version")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without changing registry")
    args = parser.parse_args()

    print("MLflow tracking URI:", mlflow.get_tracking_uri())
    print("Primary alias:", args.alias)
    print("Also prod    :", args.also_prod)
    print("Dry run      :", args.dry_run)

    for exp_name, reg_name, artifact_path in CONFIG:
        print(f"\n--- Promote pipeline: {reg_name} from {exp_name} ---")

        version = register_latest_if_needed(exp_name, reg_name, artifact_path)

        if args.dry_run:
            print(f"[DRY RUN] Would set alias '{args.alias}' -> {reg_name} v{version}")
            if args.also_prod:
                print(f"[DRY RUN] Would set alias 'prod' -> {reg_name} v{version}")
            continue

        promote_alias(
            reg_name,
            version,
            alias=args.alias,
            tags={"promoted_by": "promote_model.py"}
        )

        if args.also_prod:
            promote_alias(
                reg_name,
                version,
                alias="prod",
                tags={"promoted_by": "promote_model.py", "approval": "manual"}
            )

        # Optional: show aliases after update
        try:
            list_aliases(reg_name)
        except Exception as e:
            print("Could not list aliases:", e)


if __name__ == "__main__":
    main()
