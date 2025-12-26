# Health Insurance ML Pipeline - Commands Cheatsheet
runs masterpipeline with 25 notebooks and e2e test and model registration
./run_pipeline_clean.sh --from-index 23

# For promoting the registered models
Promote latest versions to staging
python scripts/promote_model.py --alias staging

Promote latest versions to prod
python scripts/promote_model.py --alias prod

Promote to UAT (or any custom alias)
python scripts/promote_model.py --alias uat

Promote to staging and prod in one run
python scripts/promote_model.py --alias staging --also-prod

Test without changing anything
python scripts/promote_model.py --alias prod --dry-run

# to run mlflow
./scripts/run_mlflow_ui.sh 5000

# To run unit and integration tests

To run Unit tests
pytest tests/unit -m unit -v

To run integration tests
RUN_LOCAL_SPARK=1 LOCAL_GOLD_BASE=data/gold_sample pytest tests/integration -m integration -v

For both test cases to run 
pytest tests/unit -m unit -v && RUN_LOCAL_SPARK=1 LOCAL_GOLD_BASE=data/gold_sample pytest tests/integration -m integration -v

# to run all ml tests
python -m pytest tests/unit/test_ml_models.py tests/unit/test_data_pipeline.py tests/unit/test_feature_engineering.py -v

# to run dataquality monitoring,profiling,model evaluation on one time
python src/dq_reporting.py && python src/profiling.py && python scripts/model_evaluation.py





# ########################################################################################

# Option 1 - Get Everything (Recommended):

./run_pipeline_clean.sh --from-index 20 && \
python src/dq_reporting.py && \
python src/profiling.py && \
python scripts/model_evaluation.py

# Option 2 - Just Pipeline:
./run_pipeline_clean.sh --from-index 20

# Option 3 - Pipeline first, then monitoring separately:
# Run pipeline
./run_pipeline_clean.sh --from-index 20

# After it completes, run monitoring:
python src/dq_reporting.py
python src/profiling.py
python scripts/model_evaluation.py

------------------------------------------------------------------------------------

## 🚀 Most Used Commands

### Run E2E Tests Only (Fastest)
```bash
python Master_Run_Pipeline.py --tests-only
```
**Time:** ~2 seconds | **Use:** Quick validation before full pipeline

### Run E2E Tests with pytest
```bash
pytest tests/test_pipeline_e2e.py -v
```
**Time:** ~2 seconds | **Use:** Direct test execution

### Run Full Pipeline with Tests
```bash
python Master_Run_Pipeline.py
```
**Time:** 60-120 minutes | **Use:** Complete production run

### Run Full Pipeline (Clean - Suppresses Logs)
```bash
./run_pipeline_clean.sh
```
**Time:** 60-120 minutes | **Use:** Production run with minimal log noise

### Run Pipeline Without Tests (Faster)
```bash
python Master_Run_Pipeline.py --skip-tests
```
**Time:** 60-120 minutes | **Use:** Skip tests for faster iteration

### Resume Pipeline from Notebook #10
```bash
python Master_Run_Pipeline.py --from-index 10
```
**Time:** Variable | **Use:** Continue after failure

### Resume from Notebook #10 (Clean)
```bash
./run_pipeline_clean.sh --from-index 10
```
**Time:** Variable | **Use:** Resume with suppressed logs

---

## 🧹 Clean Pipeline Runner

### What is `run_pipeline_clean.sh`?
Shell script that runs the full pipeline while **suppressing Spark, Hadoop, Ivy, and warning logs** for a cleaner console output.

### Setup (Run Once)
```bash
# Make script executable
chmod +x run_pipeline_clean.sh
```

### Run Clean Pipeline
```bash
# Full pipeline with suppressed logs
./run_pipeline_clean.sh

# With tests only
./run_pipeline_clean.sh --tests-only

# Skip tests
./run_pipeline_clean.sh --skip-tests

# Resume from notebook 12
./run_pipeline_clean.sh --from-index 12
```

### What Gets Suppressed
✅ Spark verbose logs  
✅ Hadoop logs  
✅ Ivy cache logs  
✅ Python warnings  
✅ Protocol buffer warnings  
❌ **Stdout preserved** (actual output still visible)

### Environment Variables Set
```bash
PYTHONWARNINGS=ignore          # Suppress Python warnings
SPARK_LOCAL_IP=127.0.0.1       # Localhost only
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python  # Use Python impl
```

### Usage Examples
```bash
# Clean full run (60-120 min with quiet output)
./run_pipeline_clean.sh

# Clean test-only run (2 sec)
./run_pipeline_clean.sh --tests-only

# Clean pipeline skip tests (60-120 min)
./run_pipeline_clean.sh --skip-tests

# Clean resume from failure (with from-index)
./run_pipeline_clean.sh --from-index 15
```

### When to Use
- **Production runs:** Clean output for monitoring
- **CI/CD pipelines:** Reduced log spam in build logs
- **Long-running jobs:** Cleaner terminal for visual monitoring
- **Parallel terminals:** Less distracting output while testing

### When NOT to Use
- **Debugging:** Need verbose Spark logs for troubleshooting
- **First-time setup:** Use regular Python command to catch issues
- **Performance analysis:** May miss optimization warnings

---

### Show Help
```bash
python Master_Run_Pipeline.py --help
pytest tests/test_pipeline_e2e.py --help
```

### List All Commands
```bash
python Master_Run_Pipeline.py -h
```

---

## 🔍 Testing Commands

### Verbose Test Output
```bash
pytest tests/test_pipeline_e2e.py -vv
```

### Stop on First Failure
```bash
pytest tests/test_pipeline_e2e.py -x
```

### Show Print Statements
```bash
pytest tests/test_pipeline_e2e.py -s
```

### Run Specific Test
```bash
pytest tests/test_pipeline_e2e.py::test_end_to_end_pipeline -v
```

### Run with Timeout (seconds)
```bash
pytest tests/test_pipeline_e2e.py --timeout=300
```

---

## 📁 File Operations

### Create Logs Directory
```bash
mkdir -p logs
```

### View Test Log
```bash
tail -50 logs/test_e2e.log
```

### View All Pipeline Reports
```bash
ls -lh run_reports/
```

### Pretty Print Pipeline Report
```bash
cat run_reports/run_*.json | python -m json.tool
```

### Find All Notebooks
```bash
find . -name "*.ipynb" -type f | wc -l
```

---

## 🔧 Development Workflows

### Parallel Development
```bash
# Terminal 1
python Master_Run_Pipeline.py --from-index 15

# Terminal 2
pytest tests/test_pipeline_e2e.py -v
```

### Test After Development
```bash
# After editing notebooks
pytest tests/test_pipeline_e2e.py -v

# If tests pass, resume pipeline
python Master_Run_Pipeline.py --from-index <LAST_FAILED_INDEX>
```

### Full Validation Pipeline
```bash
# 1. Quick test
python Master_Run_Pipeline.py --tests-only

# 2. Full pipeline
python Master_Run_Pipeline.py

# 3. Performance check
python src/profiling.py

# 4. Quality check
python src/dq_reporting.py

# 5. Model evaluation
python scripts/model_evaluation.py
```

---

## 🐛 Troubleshooting

### Fix Protobuf Issue
```bash
pip install --force-reinstall --no-cache-dir protobuf==5.26.1
```

### Reinstall pytest
```bash
pip install --upgrade pytest
```

### Check Python Version
```bash
python --version
```

### Clear pytest Cache
```bash
rm -rf .pytest_cache
```

### Restart Everything
```bash
# Clear cache and logs
rm -rf .pytest_cache logs/*
mkdir -p logs

# Run tests fresh
pytest tests/test_pipeline_e2e.py -v
```

---

## 📊 Phase 4 Component Commands

### Data Quality Reporting
```bash
python src/dq_reporting.py
```

### Performance Profiling
```bash
python src/profiling.py
```

### Model Evaluation
```bash
python scripts/model_evaluation.py
```

### GCP Deployment
```bash
cd gcp/terraform
terraform init
terraform plan
terraform apply
```

---

## 📚 Documentation

### View Quick Reference
```bash
cat E2E_TESTING_QUICK_REFERENCE.md
```

### View Full Guide
```bash
cat E2E_TESTING_USAGE.md
```

### View Phase 4 Architecture
```bash
cat PHASE_4_DOCUMENTATION.md
```

### View GCP Setup
```bash
cat gcp/README_GCP_SETUP.md
```

---

## 🎯 Command Decision Tree

```
Do you want to...?

├─ Test ONLY (2 sec)?
│  ├─ python Master_Run_Pipeline.py --tests-only
│  └─ ./run_pipeline_clean.sh --tests-only  (cleaner)
│
├─ Run FULL pipeline (60+ min)?
│  ├─ python Master_Run_Pipeline.py
│  └─ ./run_pipeline_clean.sh  (cleaner)
│
├─ Resume from failure?
│  ├─ python Master_Run_Pipeline.py --from-index <N>
│  └─ ./run_pipeline_clean.sh --from-index <N>  (cleaner)
│
├─ Skip tests for speed?
│  ├─ python Master_Run_Pipeline.py --skip-tests
│  └─ ./run_pipeline_clean.sh --skip-tests  (cleaner)
│
├─ Run tests directly?
│  └─ pytest tests/test_pipeline_e2e.py -v
│
├─ Check performance?
│  └─ python src/profiling.py
│
├─ Check data quality?
│  └─ python src/dq_reporting.py
│
├─ Evaluate models?
│  └─ python scripts/model_evaluation.py
│
└─ Deploy to GCP?
   └─ cd gcp/terraform && terraform apply
```

---

## 🚨 Quick Fixes (Copy & Paste)

```bash
# Setup: Make clean script executable
chmod +x run_pipeline_clean.sh

# All at once: Create logs dir + run tests
mkdir -p logs && python Master_Run_Pipeline.py --tests-only

# Clean tests only (minimal output)
./run_pipeline_clean.sh --tests-only

# Clear everything + fresh test
rm -rf .pytest_cache logs/* && python Master_Run_Pipeline.py --tests-only

# Fix + run tests
pip install --force-reinstall --no-cache-dir protobuf==5.26.1 && pytest tests/test_pipeline_e2e.py -v

# Resume from notebook 12 (clean output)
./run_pipeline_clean.sh --from-index 12

# Full validation (clean - tests + pipeline + quality + models)
./run_pipeline_clean.sh && python src/dq_reporting.py && python scripts/model_evaluation.py

# Production run (absolutely quiet)
nohup ./run_pipeline_clean.sh > /tmp/pipeline.log 2>&1 &
```

---

## 📈 Expected Output

### Successful E2E Test
```
================================================================================
PHASE 4: END-TO-END PIPELINE TESTING
================================================================================
collected 3 items

test_end_to_end_pipeline PASSED          [ 33%]
test_pipeline_execution_time PASSED      [ 66%]
test_all_notebooks_exist PASSED          [100%]

============================================================= 3 passed in 2.19s

✅ All E2E tests passed!
```

### Failed Test (Example)
```
FAILED tests/test_pipeline_e2e.py::test_all_notebooks_exist

AssertionError: Notebook not found: _01_Bronze/...

❌ Some E2E tests failed. Review output above.
```

---

## 💡 Pro Tips

1. **Always start with tests:** `--tests-only` catches issues fast
2. **Use --from-index:** Don't rerun from beginning after failure
3. **Check logs:** `logs/test_e2e.log` has detailed info
4. **Run in background:** `nohup python Master_Run_Pipeline.py &`
5. **Monitor progress:** `tail -f run_reports/*.json` in another terminal
6. **Parallel validation:** Run tests + pipeline in 2 terminals simultaneously

---

## 🔗 Related Commands

```bash
# Version checks
python --version
pip --version
pytest --version

# Configuration
cat pytest.ini              # Pytest config
cat setup.py               # Project setup
cat requirements.txt       # Dependencies

# Git (if applicable)
git status                 # Check status
git log --oneline -10      # Recent commits
git diff                   # See changes
```

---

**Last Updated:** 2025-12-22  
**Framework:** Health Insurance ML Pipeline - Phase 4  
**Status:** Production Ready
