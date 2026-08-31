# MIRANOAH

**すべてを見渡し、一つも取りこぼさない。**

Slack上の会話からタスク・Todo・期限・プロジェクト・進捗・リスクを抽出し、組織全体の仕事を一元管理するAI PMOです。

## Architecture

- `apps/web`: Next.js dashboard
- `apps/api`: FastAPI REST API / Slack event receiver
- `apps/worker`: background AI / queue worker
- PostgreSQL: source of truth
- Redis: job queue / short-lived cache
- Railway: production hosting target

## Local start

```bash
cp .env.example .env
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000
- API health: http://localhost:8000/health

## Initial operating policy

- Slack DM: excluded
- High-confidence tasks: auto-create
- AI-inferred deadlines: AI Review
- Todo generation: automatic for all Tasks
- AI reminders: automatic
- Tasks without deadline: admin review
- High-confidence completion: auto-complete
- Projects: candidate only, no auto-create
- Assignee changes: AI suggestions only
- Daily Digest: personal DM
- Manager Digest: Slack channel
- Workload: Manager and above
- Raw Slack retention: 180 days
- Google Calendar / Drive / Notion: initial-release integrations

## Permission model

Workspace roles:

- `ADMIN`
- `MANAGER`
- `PLAYER`

Permissions are resolved from:

`Workspace Role + Team Role + Project Role + Explicit Override`

Explicit `DENY` always wins.
