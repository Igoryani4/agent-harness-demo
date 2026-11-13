#!/usr/bin/env bash
set -e
set -a; source .env; set +a
git -C workspace checkout -- .
python -m orchestrator.graph "fix failing test in workspace" --yes