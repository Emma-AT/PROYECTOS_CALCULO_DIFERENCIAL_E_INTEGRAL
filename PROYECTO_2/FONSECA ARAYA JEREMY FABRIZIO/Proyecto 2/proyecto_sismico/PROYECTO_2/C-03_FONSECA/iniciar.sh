#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    if ! python3 -m venv .venv; then
        echo 'Falta soporte venv. En WSL Ubuntu: sudo apt update y sudo apt install python3-venv'
        echo 'Después volvé a ejecutar: bash iniciar.sh'
        exit 1
    fi
fi
if [[ ! -f .venv/requisitos.sha256 ]] || ! sha256sum --check --status .venv/requisitos.sha256; then
    .venv/bin/python -m pip install -r requirements.txt
    sha256sum requirements.txt > .venv/requisitos.sha256
fi
exec .venv/bin/python -m streamlit run app.py
