from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from tinyfish import TinyFish

from src.config import UserPreferences, get_api_key

logger = logging.getLogger("letmesee.scraper")

DEFAULT_RECENCY_MINUTES = 1440
MAX_SEARCH_PAGE = 10

# Job boards used for discovery, with an emphasis on India and tech roles.
JOB_BOARD_DOMAINS = (
    "naukri.com",
    "linkedin.com",
    "indeed.com",
    "indeed.co.in",
    "foundit.in",
    "glassdoor.com",
    "instahyre.com",
    "hirist.tech",
    "cutshort.io",
    "wellfound.com",
)

# Patterns that are category directories or search forms rather than specific job listings
EXCLUDED_URL_PATTERNS = (
    "/jobs/search",
    "/q-remote-",
    "/categories/",
    "/role/r/",
    "/jobs/collections",
    "/explore",
    "/browse",
)


def _build_search_query(preferences: UserPreferences) -> str:
    parts: list[str] = [preferences.role]
    if preferences.keywords:
        parts.append(" ".join(preferences.keywords[:4]))
    if preferences.location:
        parts.append(preferences.location)
    if preferences.seniority and preferences.seniority.casefold() not in ("any level", "all"):
        parts.append(preferences.seniority)
    if preferences.remote_only and "remote" not in preferences.location.casefold():
        parts.append("Remote")

    board_filter = " OR ".join(f"site:{domain}" for domain in JOB_BOARD_DOMAINS)
    parts.append(f"({board_filter})")
    return " ".join(parts)


def _normalize_url(url: str) -> str | None:
    candidate = (url or "").strip()
    if not candidate:
        return None
    if not candidate.startswith(("https://", "http://")):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower().removeprefix("www.")
    if not any(host == domain or host.endswith("." + domain) for domain in JOB_BOARD_DOMAINS):
        return None
    if host.endswith("linkedin.com") and "/jobs/view/" not in parsed.path.lower():
        return None
    # Strip tracking query strings
    clean_url = f"{parsed.scheme}://{parsed.hostname}{parsed.path}"
    lower_url = clean_url.lower()
    for pattern in EXCLUDED_URL_PATTERNS:
        if pattern in lower_url:
            return None
    return clean_url


def discover_job_urls(
    preferences: UserPreferences,
    *,
    page: int = 0,
    recency_minutes: int = DEFAULT_RECENCY_MINUTES,
) -> list[dict[str, Any]]:
    if not 0 <= page <= MAX_SEARCH_PAGE:
        raise ValueError(f"page must be between 0 and {MAX_SEARCH_PAGE}.")
    if not 1 <= recency_minutes <= 5_256_000:
        raise ValueError("recency_minutes must be between 1 and 5,256,000.")

    client = TinyFish(api_key=get_api_key())
    query = _build_search_query(preferences)
    logger.info("Executing TinyFish Search discovery: %s", query)

    try:
        response = client.search.query(
            query=query,
            language="en",
            recency_minutes=recency_minutes,
            page=page,
        )
    except Exception as exc:
        raise RuntimeError(f"TinyFish Search failed ({type(exc).__name__}): {exc}") from exc

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in getattr(response, "results", []) or []:
        raw_url = str(getattr(item, "url", "") or "")
        url = _normalize_url(raw_url)
        if not url or url in seen:
            continue
        seen.add(url)
        title = str(getattr(item, "title", "") or "").strip()
        snippet = str(getattr(item, "snippet", "") or "").strip()
        results.append({
            "title": title or "Job Opening",
            "url": url,
            "snippet": snippet,
        })

    # If ATS search yielded few results, supplement with broad careers query
    if len(results) < 4:
        broad_parts = [preferences.role, preferences.location]
        if preferences.keywords:
            broad_parts.append(" ".join(preferences.keywords[:2]))
        if preferences.remote_only and "remote" not in preferences.location.casefold():
            broad_parts.append("remote")
        broad_parts.append("jobs OR hiring OR \"job description\"")
        broad_parts.append(f"({ ' OR '.join(f'site:{domain}' for domain in JOB_BOARD_DOMAINS) })")
        broad_query = " ".join(broad_parts)
        try:
            broad_response = client.search.query(
                query=broad_query,
                language="en",
                recency_minutes=recency_minutes,
                page=page,
            )
            for item in getattr(broad_response, "results", []) or []:
                raw_url = str(getattr(item, "url", "") or "")
                url = _normalize_url(raw_url)
                if not url or url in seen:
                    continue
                seen.add(url)
                title = str(getattr(item, "title", "") or "").strip()
                snippet = str(getattr(item, "snippet", "") or "").strip()
                results.append({
                    "title": title or "Job Opening",
                    "url": url,
                    "snippet": snippet,
                })
        except Exception as exc:
            logger.warning("Secondary search query failed: %s", exc)

    return results


def fetch_job_contents(urls: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch clean, rendered Markdown and metadata from target job URLs using TinyFish Fetch."""
    if not urls:
        return {}

    client = TinyFish(api_key=get_api_key())
    batch = urls[:10]
    logger.info("Executing TinyFish Fetch for %d URLs", len(batch))

    results_by_url: dict[str, dict[str, Any]] = {}
    try:
        response = client.fetch.get_contents(
            batch,
            format="markdown",
            purpose="Extract job posting details including title, company, location, requirements, and responsibilities.",
        )
        for item in getattr(response, "results", []) or []:
            url = getattr(item, "url", None)
            if url:
                results_by_url[url] = {
                    "title": str(getattr(item, "title", "") or "").strip(),
                    "text": str(getattr(item, "text", "") or "").strip(),
                    "description": str(getattr(item, "description", "") or "").strip(),
                    "published_date": getattr(item, "published_date", None),
                }
    except Exception as exc:
        logger.warning("TinyFish Fetch failed on batch: %s", exc)

    return results_by_url


def run_agent_extraction(
    url: str,
    goal: str = "Extract the official job title, hiring company name, primary location, seniority level, and a concise 2-sentence summary of the role.",
) -> dict[str, Any] | None:
    """Use TinyFish Agent to execute autonomous browser navigation and schema-enforced extraction."""
    client = TinyFish(api_key=get_api_key())
    logger.info("Executing TinyFish Agent on %s", url)
    try:
        response = client.agent.run(
            url=url,
            goal=goal,
            output_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "seniority": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "company", "location"],
            },
            browser_profile="lite",
        )
        if response and response.result and isinstance(response.result, dict):
            logger.info("TinyFish Agent completed run %s for %s", getattr(response, "run_id", "n/a"), url)
            return response.result
    except Exception as exc:
        logger.warning("TinyFish Agent extraction skipped for %s: %s", url, exc)
    return None

