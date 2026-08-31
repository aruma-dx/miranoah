# Railway deployment map

Create one Railway project: `MIRANOAH`.

## Services

1. `miranoah-web`
   - Source: this repository
   - Dockerfile: `apps/web/Dockerfile`
   - Public domain: enabled
   - Variables:
     - `NEXT_PUBLIC_API_BASE_URL=https://<miranoah-api-domain>`

2. `miranoah-api`
   - Source: this repository
   - Dockerfile: `apps/api/Dockerfile`
   - Public domain: enabled
   - Health path: `/health`
   - Variables: copy `.env.example` and use Railway references for Postgres/Redis.

3. `miranoah-worker`
   - Source: this repository
   - Dockerfile: `apps/worker/Dockerfile`
   - Public domain: disabled
   - Variables: same DB/Redis/OpenAI variables as API.

4. PostgreSQL
   - Railway PostgreSQL template/service

5. Redis
   - Railway Redis template/service

## Environments

Use at minimum:

- `staging`
- `production`

Never share database or Slack credentials across these environments.

## Slack Event URL

Production:

`https://<api-domain>/api/v1/slack/events`

DM ingestion is intentionally ignored by MIRANOAH policy.
