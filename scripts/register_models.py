from pathlib import Path
from datetime import datetime, timezone
import mlflow
from mlflow.tracking import MlflowClient

PROJECT_ROOT = Path("/Users/manojrammopati/Public/Projects/health_insurance_project")

# Must match your notebook tracking URI
TRACKING_URI = f"file:{PROJECT_ROOT / 'mlruns'}"
mlflow.set_tracking_uri(TRACKING_URI)

client = MlflowClient()

CONFIG = [
    # (experiment_name, registered_model_name, artifact_path_logged_in_notebook)
    ("health_policy_churn",           "health_policy_churn_model",   "best_policy_churn_model"),
    ("health_claims_risk_fraud",      "health_claims_fraud_model",   "fraud_best_model"),
    ("health_claims_risk_high_cost",  "health_high_cost_model",      "high_cost_best_model"),
]


def latest_finished_run_id(experiment_name: str) -> str:
    exp = client.get_experiment_by_name(experiment_name)
    if exp is None:
        raise RuntimeError(f"Experiment not found: {experiment_name}")

    # First try to find FINISHED runs
    df = mlflow.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    
    # If no FINISHED runs, get the latest run (which should be ended)
    if df is None or len(df) == 0:
        print(f"⚠️  No FINISHED runs found, fetching latest run (may be ended)...")
        df = mlflow.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["attributes.start_time DESC"],
            max_results=1,
        )
    
    if df is None or len(df) == 0:
        raise RuntimeError(f"No runs found for experiment: {experiment_name}")

    return df.loc[0, "run_id"]


def ensure_registered_model(name: str):
    try:
        client.create_registered_model(name)
        print(f"✅ Created registered model: {name}")
    except Exception:
        # already exists
        pass


def already_registered(model_name: str, run_id: str) -> bool:
    versions = client.search_model_versions(f"name='{model_name}'")
    return any(getattr(v, "run_id", None) == run_id for v in versions)


def copy_run_tags_to_model_version(run_id: str, model_name: str, version: str, extra_tags: dict | None = None):
    """
    Copies MLflow RUN tags into MODEL VERSION tags so they show up in the Model Registry UI.
    Also adds a few useful audit tags (timestamps, run_id, etc.).
    """
    run = client.get_run(run_id)

    # Run tags (whatever you set in notebooks via mlflow.set_tag / mlflow.set_tags)
    run_tags = dict(run.data.tags or {})

    # Add some common audit tags
    run_tags.update({
        "source_run_id": run_id,
        "registered_at_utc": datetime.now(timezone.utc).isoformat(),
        "registered_by": "scripts/register_models.py",
    })

    # Merge user-provided tags (overrides)
    if extra_tags:
        run_tags.update({str(k): str(v) for k, v in extra_tags.items()})

    # Write as model version tags (must be strings)
    for k, v in run_tags.items():
        try:
            client.set_model_version_tag(model_name, version, str(k), str(v))
        except Exception as e:
            print(f"⚠️ Could not set tag {k} on {model_name} v{version}: {e}")

    print(f"🏷️  Copied {len(run_tags)} tags to {model_name} v{version}")


def register_latest(experiment_name: str, model_name: str, artifact_path: str):
    run_id = latest_finished_run_id(experiment_name)
    model_uri = f"runs:/{run_id}/{artifact_path}"

    ensure_registered_model(model_name)

    if already_registered(model_name, run_id):
        print(f"⚠️ Skip: {model_name} already has a version for run_id={run_id}")
        return

    mv = client.create_model_version(
        name=model_name,
        source=model_uri,
        run_id=run_id
    )
    print(f"✅ Registered {model_name} v{mv.version} from run_id={run_id}")

    # Copy run tags -> model version tags so they appear in the registry UI
    copy_run_tags_to_model_version(
        run_id=run_id,
        model_name=model_name,
        version=str(mv.version),
        extra_tags={
            "experiment_name": experiment_name,
            "artifact_path": artifact_path,
            "lifecycle": "registered",
        }
    )


if __name__ == "__main__":
    print("MLflow tracking URI:", mlflow.get_tracking_uri())
    for exp_name, reg_name, artifact_path in CONFIG:
        print(f"\n--- Registering: {reg_name} from experiment {exp_name} ---")
        register_latest(exp_name, reg_name, artifact_path)
