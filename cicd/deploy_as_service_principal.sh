#!/bin/bash
# Deploy and run the `cicd` target as a service principal from your laptop, the way cicd/gitlab-ci.yml does
# (OAuth M2M). Creates a temporary OAuth secret, never prints it, and always deletes it at the end.
#
#   PROFILE=<admin CLI profile> SP_NAME=hytech-ws-cicd ./cicd/deploy_as_service_principal.sh
#
# Needs: the service principal and its grants (docs/cicd_demo.md, one-time setup) and workspace-admin rights
# on PROFILE to create and delete the secret.
set -euo pipefail

PROFILE=${PROFILE:-fe-vm-zh-serverless}
SP_NAME=${SP_NAME:-hytech-ws-cicd}
REPO=$(cd "$(dirname "$0")/.." && pwd)
LOG=${LOG:-/tmp/cicd_run.log}

HOST=$(databricks auth describe -p "$PROFILE" | sed -n 's/^Host: //p' | head -1)
read -r SP_ID APP_ID < <(databricks service-principals list --filter "displayName eq \"$SP_NAME\"" -p "$PROFILE" -o json |
  python3 -c 'import json, sys; d = json.load(sys.stdin); d = d if isinstance(d, list) else d.get("Resources", []); print(d[0]["id"], d[0]["applicationId"])')
echo "workspace: $HOST | service principal: $SP_NAME ($APP_ID)"

umask 077
SECRET_JSON=$(mktemp)
EMPTY_CFG=$(mktemp)
SECRET_ID=""

cleanup() {
  if [ -n "$SECRET_ID" ]; then
    databricks service-principal-secrets-proxy delete "$SP_ID" "$SECRET_ID" -p "$PROFILE" && echo "✅ secret $SECRET_ID deleted"
  fi
  rm -f "$SECRET_JSON" "$EMPTY_CFG"
}
trap cleanup EXIT

databricks service-principal-secrets-proxy create "$SP_ID" -p "$PROFILE" -o json > "$SECRET_JSON"
SECRET_ID=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["id"])' "$SECRET_JSON")
echo "✅ temporary secret $SECRET_ID created"

# Only the service principal's credentials, as in CI: hide the CLI profiles from these commands.
as_sp() {
  DATABRICKS_CONFIG_FILE="$EMPTY_CFG" DATABRICKS_HOST="$HOST" DATABRICKS_CLIENT_ID="$APP_ID" \
  DATABRICKS_CLIENT_SECRET="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["secret"])' "$SECRET_JSON")" \
  BUNDLE_VAR_cicd_service_principal="$APP_ID" "$@"
}

cd "$REPO"
as_sp databricks current-user me -o json | python3 -c 'import json, sys; d = json.load(sys.stdin); print("deploying as:", d["userName"], "/", d.get("displayName"))'
as_sp databricks bundle validate -t cicd
as_sp databricks bundle deploy -t cicd --auto-approve
echo "running the solution job as the service principal (about 4 minutes)..."
as_sp databricks bundle run -t cicd hytech_daily_trading_reporting_solution 2>&1 | tee "$LOG"
