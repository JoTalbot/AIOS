#!/bin/bash
set -e

echo "🔨 Building AIOS SDK v11.0.0..."
cd sdk
pip install build wheel
python -m build

echo "✅ SDK built successfully in AIOS/sdk/dist/"
