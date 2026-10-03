# CI/CD demo — deploy as a service principal (M5, about 10 minutes)

**Message:** in production nobody deploys by hand. A merge to the default branch runs GitLab CI, which deploys
the bundle as a service principal. The jobs and the pipeline are owned by and run as that service principal,
and people get view rights only. This is Hytech's "no direct prod access" priority, and *Implementing CI/CD* is
10% of the Data Engineer Associate exam.

## What to show

1. **`databricks.yml`: one bundle, three targets**

   | Target | Mode | Who deploys | Notes |
   |---|---|---|---|
   | `dev` | development | each engineer | Names prefixed `[dev <you>]`, schedules and triggers paused, own copy |
   | `prod` | production | workshop admin | The shared workshop deployment (root path in `/Workspace/Shared` so several admins can redeploy one copy) |
   | `cicd` | production | **service principal only** | `run_as` the service principal, root path in its home folder, `users` get CAN_VIEW, names prefixed `[cicd]`, own schema `solutions_cicd` |

2. **`cicd/gitlab-ci.yml`:** `validate` on merge requests and `deploy` on the default branch. Credentials are
   masked and protected CI variables. `resource_group` allows one deployment at a time.
3. **Live deploy as the service principal** from the laptop, with the same commands the CI job runs:

   ```bash
   PROFILE=<admin CLI profile> ./cicd/deploy_as_service_principal.sh
   ```

   The script creates a temporary OAuth secret and hides your own CLI profiles. It then runs `bundle validate`
   (`User:` shows the application ID, not a person), `bundle deploy` and `bundle run` as the service principal,
   and deletes the secret when it exits, even on failure. Deploying takes about a minute and the job about four.

4. **In the workspace:** open job `[cicd] hytech_daily_trading_reporting_solution`. *Run as* and owner are the
   service principal. Participants can view it but not edit it. The deployed files sit in the service
   principal's home folder.

## One-time setup on the demo workspace (instructor, about 10 minutes)

1. **Create the service principal** (workspace admin):

   ```bash
   databricks service-principals create -p <profile> \
     --json '{"displayName": "hytech-ws-cicd", "entitlements": [{"value": "workspace-access"}]}'
   ```

   Note `id` (for the secret) and `applicationId` (for grants and `DATABRICKS_CLIENT_ID`).
2. **OAuth secret, only for GitLab:** *Settings → Identity and access → Service principals → hytech-ws-cicd →
   Secrets → Generate secret*. It is shown once; store it only as a masked, protected CI variable. The demo
   script creates and deletes its own temporary secret, so the demo workspace keeps none.
3. **Unity Catalog grants** (SQL editor, as the catalog owner):

   ```sql
   CREATE SCHEMA IF NOT EXISTS hytech_de_workshop.solutions_cicd
     COMMENT 'CI/CD demo: owned and written by the service principal';
   ALTER SCHEMA hytech_de_workshop.solutions_cicd OWNER TO `<application-id>`;
   GRANT USE CATALOG ON CATALOG hytech_de_workshop TO `<application-id>`;
   GRANT USE SCHEMA ON SCHEMA hytech_de_workshop.raw TO `<application-id>`;
   GRANT READ VOLUME ON VOLUME hytech_de_workshop.raw.landing TO `<application-id>`;
   GRANT READ VOLUME ON VOLUME hytech_de_workshop.raw.ref TO `<application-id>`;
   ```

   The service principal owns its schema, as production objects should be owned by a service principal or a
   group rather than a person. It only needs read access to the landing zone.
4. **Do one deploy and one run before the workshop** (step 3 of *What to show*) and check the run is green.

## Notes from the FEVM dry run (3 Oct 2026)

- `hytech-ws-cicd` deployed and ran the `cicd` target over OAuth M2M. The job and pipeline are owned by it and
  run as it, `users` have CAN VIEW, and all 23 tables in `solutions_cicd` are owned by it. The run was green
  in about 3.5 minutes.
- The root path in the service principal's home folder works without creating the folder first.
- Even the catalog owner gets `INSUFFICIENT_PERMISSIONS` on the service principal's schema: no `USE SCHEMA`
  until someone grants it. This is least privilege in action and a good talking point. To show the data, the
  catalog owner can grant `USE SCHEMA` and `SELECT` on `solutions_cicd` to a read-only group.

## For Hytech (Triones / Robin)

- Use one service principal per environment (for example `sp-de-prod`) with workspace access, and keep its
  OAuth secret only in masked, protected GitLab variables. Rotate the secret.
- The service principal owns the production schemas; people get read access.
- Protect the default branch, require merge-request approval, and run `bundle validate` on every merge request.
- Set `workspace.host` per target in `databricks.yml` (the host cannot come from a variable).
- Runners in mainland China may not reach github.com: bake the Databricks CLI into the runner image.
