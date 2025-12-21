#!/bin/bash
# Clean Pipeline Runner - Suppresses Spark/Hadoop/Ivy logs
# Usage: ./run_pipeline_clean.sh [--from-index N]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PYTHONWARNINGS=ignore
export SPARK_LOCAL_IP=127.0.0.1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

cd "$PROJECT_ROOT"

# Run pipeline with stderr suppressed (hides most warnings but keeps stdout)
python Master_Run_Pipeline.py "$@" 2>/dev/null







