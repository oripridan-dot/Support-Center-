#!/bin/bash
# Helper script to ingest a single brand
BRAND_NAME=$1

if [ -z "$BRAND_NAME" ]; then
    echo "Usage: ./scripts/ingest_single_brand.sh <brand_name>"
    exit 1
fi

cd /workspaces/Support-Center-/backend
python3 scripts/ingest_halilit_brands.py --brand "$BRAND_NAME"
