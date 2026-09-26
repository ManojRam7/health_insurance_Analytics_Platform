# Architecture

## Layers

```text
Kaggle files + generated fields
        |
        v
BRONZE   raw Delta tables: policies, members, claims, providers (no transformation)
        |
        v
SILVER   schema enforcement, key checks, de-duplication, date and money validation,
         quarantine tables with reason codes, row-count metrics
        |
        v
GOLD     facts:        fact_policies, fact_members, fact_claims
         dimensions:   dim_channel, dim_product_line, dim_region, dim_member_segment,
                       dim_claim_type, dim_providers
         star schemas: star_policies, star_members, star_claims
         data marts:   dm_policy_retention, dm_member_value, dm_claims_experience
         features:     ft_policy_churn, ft_claims_risk (with train/test split columns)
        |
        +--> models: policy churn, fraudulent claim, high-cost claim (Spark ML, MLflow)
        |        --> scored_policy_churn, scored claim tables --> ml_monitoring
        +--> reporting views (vw_*) for Power BI
        +--> dq_monitoring
```

Storage is local Delta tables by default; the same notebooks read and write ADLS Gen2 containers
(`rawdata`, `silverdata`, `golddata`) when service principal credentials are supplied through
environment variables or Key Vault (`config/config.py`).

## Silver rules

| Check | Example |
|---|---|
| Schema | Read with an explicit schema and consistent column types |
| Primary key | Null or duplicate keys quarantined (`Claim_ID`, `Policy_ID`, `Member_ID`, `Provider_ID`) |
| Foreign key | Claims must reference a known provider; unlabelled providers are added as `assumed_clean` |
| Dates | Invalid dates repaired where possible, otherwise set to null and flagged (`dq_date_valid`) |
| Money | Negative or implausible amounts flagged (`dq_money_valid`) |
| Features | Derived fields such as `Days_To_Settle`, age and BMI bands |

Rejected rows go to `_quarantine/<entity>/<rule>` with the rule name, and each notebook logs row
counts before and after so every drop is accounted for. Each entity has a `Report.txt` next to its
notebook describing the transformations.

## Machine learning

| Use case | Feature table | Label | Candidates | Selection |
|---|---|---|---|---|
| Policy churn | `ft_policy_churn` | churn flag | Logistic regression, random forest, gradient-boosted trees | ROC AUC on the test split |
| Fraudulent claim | `ft_claims_risk` | claim-level fraud label | Logistic regression, random forest | ROC AUC |
| High-cost claim | `ft_claims_risk` | top-decile claim amount | Logistic regression, random forest | ROC AUC |

Each training notebook logs parameters, metrics and feature importances to MLflow, saves the
selected pipeline with a version tag, and appends its metrics to `ml_monitoring`.
`scripts/register_models.py` and `scripts/promote_model.py` move a model through the MLflow
registry; the batch-scoring notebooks load the current version and write scored tables.

## Orchestration and CI

- `Master_Run_Pipeline.py` executes the notebooks in order with `nbconvert`, records the duration
  and status of each step, and writes a JSON and Markdown run report.
- `.github/workflows/ci.yml` runs formatting and lint checks, unit tests on three Python versions
  and integration tests against `data/gold_sample/`.
- Schema snapshots in `schemas/gold/` back contract tests that fail if a gold table changes shape
  unexpectedly.
