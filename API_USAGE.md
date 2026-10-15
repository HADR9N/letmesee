# API Usage

## Health

`GET /api/health`

```json
{"status":"ok","service":"letmesee-api"}
```

## Search

`POST /api/search`

```json
{
  "role": "Backend Engineer",
  "location": "Remote",
  "keywords": ["Python", "FastAPI"],
  "seniority": "Junior",
  "remote_only": true,
  "page": 0
}
```

The response contains `query`, `count`, `results`, `stages`, and an optional `warning`. The pipeline integrates:
1. **TinyFish Search**: High-intent job posting discovery across ATS portals and direct careers pages.
2. **TinyFish Fetch**: Batch live Markdown extraction for job descriptions, titles, and metadata.
3. **TinyFish Agent**: Autonomous browser agent verification for structured employer data.
4. **Local Multi-factor Matching**: Deduplication and relevance scoring against user preferences.

All stages (`discovery`, `fetch`, `agent`, `matching`) return `"complete"`.

## Dedicated Agent Extraction

`POST /api/agent/extract`

```json
{
  "url": "https://jobs.lever.co/example/123",
  "goal": "Extract job title, company name, location, seniority, and summary"
}
```

## Dedicated Batch Fetch

`POST /api/fetch`

```json
{
  "urls": ["https://jobs.ashbyhq.com/example/123"],
  "purpose": "Extract job posting description and requirements"
}
```

The TinyFish API key stays on the backend and must never be included in frontend code.

