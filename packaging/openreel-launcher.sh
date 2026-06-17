#!/bin/bash
export PYTHONPATH=/app/lib/openreel:${PYTHONPATH}
exec python3 /app/lib/openreel/run.py "$@"
