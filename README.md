# Health Insurance ML Pipeline

**Enterprise-Grade Machine Learning Platform for Healthcare Insurance Analytics**

[![CI](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/ci.yml?branch=main&label=CI)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/ci.yml)
[![Code Quality](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/code-quality.yml?branch=main&label=Code%20Quality)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/code-quality.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/ManojRam7/health_insurance_project/documentation.yml?branch=main&label=Docs)](https://github.com/ManojRam7/health_insurance_project/actions/workflows/documentation.yml)
[![Python](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📚 Documentation Structure

This project maintains a **concise, centralized documentation** system. Start here:

### 🎯 Essential Reading (Start Here)

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [`PROJECT_OVERVIEW.md`](./Project_Documentation/PROJECT_OVERVIEW.md) | Complete project guide with architecture, setup, and operations | 15 min |
| [`QUICK_REFERENCE.md`](./QUICK_REFERENCE.md) | Quick lookup: commands, decisions, scoring | 3 min |
| [`Architecture/ARCHITECTURE.md`](./Project_Documentation/Architecture/ARCHITECTURE.md) | Technical architecture, data flow, design patterns | 10 min |

### 🚀 Getting Started

| Document | Purpose | Read Time |
|----------|---------|-----------|
| `PROJECT_DOCUMENTATION/PROJECT_OVERVIEW.md` → "Getting Started" section | Step-by-step setup | 5 min |
| `DEPLOYMENT_ROADMAP.md` | GCP deployment & release schedule | 8 min |
| `_03_Gold/Gold_layer_documentation.md` | Gold-layer outputs and analytics context | 8 min |

### 🔍 Deep Dives

| Topic | Document | Purpose |
|-------|----------|---------|
| **Production Monitoring** | `Project_Documentation/Phase_4_Documentation/README_PRODUCTION.md` | Real-time ML monitoring, alerts, SLAs |
| **ML Model Details** | `Project_Documentation/ML_TESTS_SUMMARY/ML_TESTS_QUICK_REFERENCE.md` | Model specs, performance, features |
| **Gold Data Layer** | `_03_Gold/Gold_layer_documentation.md` | Gold marts, dimensions, and fact tables |

### 🏗️ Folder Structure

```
health_insurance_project/
├── README.md                          ← You are here
├── PROJECT_DOCUMENTATION/             ← Core documentation
│   ├── PROJECT_OVERVIEW.md            ✅ START HERE
│   ├── Architecture/ARCHITECTURE.md
│   ├── Phase_4_Documentation/         ✅ Production guide
│   └── ML_TESTS_SUMMARY/              ✅ Model specs
├── _00_Pre_Pilot/                     ✅ Data generation
├── _01_Bronze/                        ✅ Raw data ingestion
├── _02_Silver/                        ✅ Data transformation
├── _03_Gold/                          ✅ Analytics & ML
├── config/                            ✅ Pipeline configuration
├── src/                               ✅ Production utilities
├── tests/                             ✅ 127 unit tests
└── scripts/                           ✅ Operational scripts
```

---

## ⚡ Quick Access

### Most Common Tasks

| Task | File | Command |
|------|------|---------|
| Run full pipeline | `PROJECT_OVERVIEW.md` → Getting Started | `python Master_Run_Pipeline.py` |
| Check model performance | `ML_TESTS_SUMMARY/ML_TESTS_QUICK_REFERENCE.md` | Review metrics |
| Deploy to GCP | `DEPLOYMENT_ROADMAP.md` → Implementation | See deployment guide |
| Run tests | `PROJECT_OVERVIEW.md` → Testing section | `pytest tests/` |

### Docker Quick Start

```bash
# Build the image
docker build -t health-insurance-ml .

# Run the pipeline in a container
docker run --rm health-insurance-ml
```

Use Docker when you want a reproducible, isolated environment for pipeline execution.

### Key Metrics at a Glance

- ✅ **Data Volume**: 62,000+ records processed
- ✅ **Pipeline Speed**: ~15 minutes end-to-end
- ✅ **Data Quality**: 98.3/100 score
- ✅ **Model Performance**: AUC 0.856-0.912
- ✅ **Test Coverage**: 127 tests (100% pass rate)
- ✅ **Production Ready**: 9.5/10 enterprise score

---

## 🎓 Document Purposes (NOT Duplicated)

### Why Each Document Exists

1. **PROJECT_OVERVIEW.md** - Comprehensive guide (all aspects in one place)
2. **ARCHITECTURE.md** - Technical design, data models, system interactions
3. **QUICK_REFERENCE.md** - Speed lookup, decision trees, checklists
4. **Phase_4_Documentation** - Production operations & real-time monitoring
5. **ML_TESTS_SUMMARY** - Model specifications & training details
6. **DEPLOYMENT_ROADMAP.md** - Cloud deployment & release timeline
7. **Gold_layer_documentation.md** - Curated gold-layer documentation

**Eliminated:**
- ❌ 40+ timestamped run reports (execution logs, not docs)
- ❌ Redundant status reports (MAIN_BRANCH, FEATURE_BRANCH folders)
- ❌ Duplicate test summaries (consolidated to one)
- ❌ Overlapping audit reports (kept authoritative versions)

---

## 🔧 Documentation Maintenance

### Guidelines

- **Each document has ONE purpose** - no duplication
- **PROJECT_OVERVIEW.md** is the master reference
- **QUICK_REFERENCE.md** enables fast lookups
- **Specialized docs** (ARCHITECTURE, Phase_4) dig deeper into specific topics
- **All docs link to each other** for navigation

### Before Adding New Docs

Ask: "Does this already exist in PROJECT_OVERVIEW or QUICK_REFERENCE?"
- If **YES** → Add a link, don't duplicate
- If **NO** → Create it with a specific, non-overlapping purpose

---

## 🚀 Next Steps

1. **New to the project?** → Read [`PROJECT_OVERVIEW.md`](./Project_Documentation/PROJECT_OVERVIEW.md)
2. **Need quick info?** → Check [`QUICK_REFERENCE.md`](./QUICK_REFERENCE.md)
3. **Deploying to GCP?** → Follow [`DEPLOYMENT_ROADMAP.md`](./DEPLOYMENT_ROADMAP.md)
4. **Production operations?** → See [`Phase_4_Documentation`](./Project_Documentation/Phase_4_Documentation/)
5. **Gold data model details?** → Review [`Gold_layer_documentation.md`](./_03_Gold/Gold_layer_documentation.md)

---

## 📞 Support

For issues or questions:
- Check `PROJECT_OVERVIEW.md` → Troubleshooting section
- Review `Phase_4_Documentation` → Operations guide
- Run tests locally with `pytest tests/`

---

**Last Updated**: January 19, 2026  
**Status**: ✅ Production Ready (Streamlined Documentation)
