#!/bin/bash
# One-time setup: Pre-cache Ivy dependencies
# Run this ONCE before your first pipeline execution

echo "========================================="
echo "Caching Ivy Dependencies (One-time setup)"
echo "========================================="
echo ""
echo "This will download and cache all PySpark dependencies locally."
echo "This only needs to run once!"
echo ""

cd "$(dirname "$0")"

# Run the pre-cache script
python pre_cache_ivy.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete! Dependencies are now cached."
    echo ""
    echo "Next steps:"
    echo "  1. Run your pipeline: ./run_pipeline_clean.sh --from-index 0"
    echo "  2. Ivy output will be MUCH less on subsequent runs"
    echo ""
else
    echo ""
    echo "❌ Setup failed. Check the error above."
    exit 1
fi
