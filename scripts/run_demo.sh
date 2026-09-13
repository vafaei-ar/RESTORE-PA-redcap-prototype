#!/usr/bin/env bash
set -euo pipefail

python synthetic_data/generate_demo_data.py
streamlit run app/app.py
