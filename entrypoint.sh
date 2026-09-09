#!/bin/bash
set -euo pipefail

if [ "${1:-}" = "web" ]; then
    echo "🌐 Starting Golf Verifier Web Dashboard on http://localhost:8080..."
    exec streamlit run /workspace/web_app.py --server.port=8080 --server.address=0.0.0.0
else
    exec goose session
fi
