#!/bin/bash
# 从你的笔记本电脑按照 cicd/gitlab-ci.yml 的方式将 `cicd` 目标部署并运行为服务主体
# (OAuth M2M)。创建一个临时 OAuth 密钥，永不打印，最后总是删除。
# Deploy and run the `cicd` target as a service principal from your laptop, the way cicd/gitlab-ci.yml does
# (OAuth M2M). Creates a temporary OAuth secret, never prints it, and always deletes it at the end.
#
#   PROFILE=<admin CLI profile> SP_NAME=hytech-ws-cicd ./cicd/deploy_as_service_principal.sh
#
# 需要：服务主体及其授权（docs/cicd_demo.md，一次性设置）以及 PROFILE 上的工作区管理员权限
# 以创建和删除密钥。
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
    # 删除临时 OAuth 密钥 / delete temporary OAuth secret
    databricks service-principal-secrets-proxy delete "$SP_ID" "$SECRET_ID" -p "$PROFILE" && echo "✅ secret $SECRET_ID deleted"
  fi
  rm -f "$SECRET_JSON" "$EMPTY_CFG"
}
trap cleanup EXIT

databricks service-principal-secrets-proxy create "$SP_ID" -p "$PROFILE" -o json > "$SECRET_JSON"
SECRET_ID=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["id"])' "$SECRET_JSON")
echo "✅ temporary secret $SECRET_ID created"

# 仅限服务主体的凭据，如在 CI 中一样：隐藏这些命令中的 CLI 配置文件。
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
# 以服务主体身份运行参考答案作业（约 4 分钟）...
# running the solution job as the service principal (about 4 minutes)...
echo "running the solution job as the service principal (about 4 minutes)..."
as_sp databricks bundle run -t cicd hytech_daily_trading_reporting_solution 2>&1 | tee "$LOG"
