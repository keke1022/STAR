#!/bin/sh
# Explicit draft plan: mutations are printed unless --execute is supplied.
exec python3 "$(dirname "$0")/gcp_plan.py" "$@"
