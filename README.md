# Health Insurance ML Pipeline

Enterprise-grade machine learning platform for healthcare insurance analytics with an end-to-end medallion pipeline, feature engineering, model training, and batch scoring.

[![CI](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/ci.yml?branch=main&label=CI)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/ci.yml)
[![Code Quality](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/code-quality.yml?branch=main&label=Code%20Quality)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/code-quality.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/documentation.yml?branch=main&label=Docs)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/documentation.yml)
[![Python](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What This Project Delivers

- Processes 62,000+ records through Bronze, Silver, and Gold data layers
- Trains and evaluates 3 core ML models for insurance decision support
- Produces batch predictions for churn risk, fraud risk, and high-cost claims
- Tracks quality and performance with repeatable, documented workflows

### Core Business Outcomes

1. Policy churn prediction for proactive retention
2. Claim fraud detection for investigation prioritization
3. High-cost claim prediction for early intervention

---

## Architecture At A Glance

1. Bronze layer: raw ingestion and schema-preserving storage
2. Silver layer: cleansing, validation, standardization, and feature-ready transforms
3. Gold layer: facts, dimensions, marts, star schemas, and ML-ready datasets
4. ML layer: training, evaluation, versioned artifacts, and scoring outputs

For full technical architecture, see:
- [Project_Documentation/Architecture/ARCHITECTURE.md](./Project_Documentation/Architecture/ARCHITECTURE.md)
- [Project_Documentation/PROJECT_OVERVIEW.md](./Project_Documentation/PROJECT_OVERVIEW.md)

---

## Repository Map

```text
health_insurance_project/
├── Master_Run_Pipeline.py
├── config/
├── src/
├── tests/
├── _00_Pre_Pilot/
├── _01_Bronze/
├── _02_Silver/
├── _03_Gold/
├── Project_Documentation/
└── .github/workflows/
```

---

## Quick Start

### Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Run The Pipeline

```bash
python Master_Run_Pipeline.py
```

### Run Tests

```bash
pytest tests/
```

---

## Docker

```bash
docker build -t health-insurance-ml .
docker run --rm health-insurance-ml
```

Use Docker for reproducible local execution and CI parity.

---

## CI/CD And Quality Gates

- [ci.yml](./.github/workflows/ci.yml): linting + multi-version unit/integration validation
- [code-quality.yml](./.github/workflows/code-quality.yml): security and dependency checks
- [documentation.yml](./.github/workflows/documentation.yml): markdown and link validation

Issue templates are available for bug reports, feature requests, test failures, and documentation updates in [.github/ISSUE_TEMPLATE](./.github/ISSUE_TEMPLATE/).

---

## Documentation Guide

Read in this order:

1. [Project_Documentation/PROJECT_OVERVIEW.md](./Project_Documentation/PROJECT_OVERVIEW.md) for end-to-end flow
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for deployment and decision shortcuts
3. [Project_Documentation/Architecture/ARCHITECTURE.md](./Project_Documentation/Architecture/ARCHITECTURE.md) for technical design
4. [Project_Documentation/Phase_4_Documentation/README_PRODUCTION.md](./Project_Documentation/Phase_4_Documentation/README_PRODUCTION.md) for production operations
5. [Project_Documentation/ML_TESTS_SUMMARY/ML_TESTS_QUICK_REFERENCE.md](./Project_Documentation/ML_TESTS_SUMMARY/ML_TESTS_QUICK_REFERENCE.md) for ML/testing quick details
6. [_03_Gold/Gold_layer_documentation.md](./_03_Gold/Gold_layer_documentation.md) for Gold-layer outputs
7. [DEPLOYMENT_ROADMAP.md](./DEPLOYMENT_ROADMAP.md) for cloud rollout planning

---

## Operational Notes

- The project is optimized for batch ML workflows with versioned outputs.
- Current roadmap focus areas include orchestration automation and real-time serving extensions.
- Documentation is intentionally curated to avoid duplication.

---

## Support

- Open an issue using templates in [.github/ISSUE_TEMPLATE](./.github/ISSUE_TEMPLATE/)
- Review contributing standards in [CONTRIBUTING.md](./CONTRIBUTING.md)

---

**Last Updated**: June 20, 2026  
**Status**: ✅ Production Ready (Curated End-to-End Documentation)
