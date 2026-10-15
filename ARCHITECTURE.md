# Architecture

## Current flow

React preference form → `POST /api/search` → FastAPI validation → TinyFish Search (discovery) → TinyFish Fetch (live page content extraction) → TinyFish Agent (autonomous browser verification) → multi-factor scoring & ranking → structured JSON → animated results list.

## Frontend

- React + Vite + TypeScript.
- `motion` for motion/transition APIs.
- Aceternity-style Spotlight and Card Spotlight components.
- Custom CSS for the Apple-inspired editorial/brutalist visual system.

## Backend

- `api/index.py`: FastAPI endpoints (`/api/health`, `/api/search`, `/api/agent/extract`, `/api/fetch`).
- `src/config.py`: Environment loading and Pydantic `UserPreferences`.
- `src/scraper.py`: TinyFish Search discovery, TinyFish Fetch batch retrieval, and TinyFish Agent execution.
- `src/matcher.py`: Clean extraction of genuine employer names, locations, seniority, and multi-factor relevance ranking.

## Endpoints

- `GET /api/health`
- `POST /api/search`
- `POST /api/agent/extract`
- `POST /api/fetch`

## Pipeline Execution

1. **Discovery**: TinyFish Search discovers live job posting URLs across leading ATS platforms (Ashby, Lever, Greenhouse, Workable, SmartRecruiters) and direct career portals.
2. **Fetch**: TinyFish Fetch retrieves live, rendered Markdown for candidate URLs in batch mode.
3. **Agent**: TinyFish Agent autonomously navigates target listings to verify employer, role title, seniority, and location.
4. **Matching**: Multi-factor scoring matches candidate listings against user keywords, seniority, and remote preferences. All stages report `"complete"`.

