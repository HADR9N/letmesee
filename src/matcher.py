from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

from src.config import UserPreferences


class JobListing(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str
    company: str
    location: str
    url: str
    description: str | None = None
    posted_date: str | None = None
    seniority: str | None = None
    match_score: float = 0.0
    source: str | None = None


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def extract_company(
    title: str,
    url: str,
    text: str = "",
    agent_data: dict[str, Any] | None = None,
) -> str:
    """Extract clean company name from agent data, ATS URL paths, title patterns, or content."""
    if agent_data and agent_data.get("company"):
        candidate = str(agent_data["company"]).strip()
        if candidate and candidate.lower() not in ("company not identified", "unknown"):
            return candidate

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path_parts = [p for p in parsed.path.split("/") if p]

    # LinkedIn URL slug: /jobs/view/...-at-<company>-<id>
    m_url = re.search(r"-at-([a-zA-Z0-9\-]+?)(?:-\d+)?/?$", url)
    if m_url:
        cand = m_url.group(1).replace("-", " ").title()
        if len(cand) > 1 and not cand.isdigit():
            return cand

    # ATS slug detection
    for ats in ("ashbyhq.com", "lever.co", "greenhouse.io", "workable.com"):
        if ats in host and path_parts:
            slug = path_parts[0]
            if slug.lower() not in ("jobs", "apply", "careers", "q"):
                cleaned = slug.replace("-", " ").title()
                if len(cleaned) < 35:
                    return cleaned

    # Strip domain suffixes from title for cleaner matching
    clean_title = re.sub(r"\s*[-|]\s*(?:LinkedIn|Workable|Indeed|Glassdoor).*$", "", title, flags=re.IGNORECASE).strip()

    # Title patterns: Role @ Company, Role at Company [in City], Company - Role
    m_at_in = re.search(r"\bat\s+([^-\|,\(\)]+?)(?:\s+\bin\s+[^-\|,\(\)]+|\s*[-|]|$)", clean_title, re.IGNORECASE)
    if m_at_in:
        cand = m_at_in.group(1).strip()
        if 1 < len(cand) < 40 and not any(w in cand.lower() for w in ("remote", "full time", "engineer", "developer")):
            return cand

    for pattern in (
        r"@\s+([^-\|,\(\)]+)",
        r"^([^-\|]+)\s+-\s+",
        r"\s+-\s+([^-\|]+)$",
    ):
        m = re.search(pattern, clean_title, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            cand_lower = cand.lower()
            if (
                cand
                and 1 < len(cand) < 40
                and not any(
                    w in cand_lower
                    for w in (
                        "remote",
                        "full time",
                        "full-time",
                        "part-time",
                        "contract",
                        "engineer",
                        "developer",
                        "designer",
                        "manager",
                        "jobs",
                        "internship",
                    )
                )
            ):
                return cand

    # Text pattern: About <Company>
    if text:
        m = re.search(r"#+\s*About\s+([^\n#]{2,40})", text, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            cand_lower = cand.lower()
            if not any(w in cand_lower for w in ("us", "the role", "the company", "our team")):
                return cand

    # Domain fallback (ignoring job aggregators / subdomains)
    parts = host.removeprefix("www.").split(".")
    domain = parts[-2] if len(parts) >= 2 and parts[-2] not in ("co", "com", "org") else parts[0]
    if domain and domain.lower() not in ("linkedin", "indeed", "glassdoor", "wellfound", "br", "ca", "uk", "in"):
        return domain.capitalize()

    return "Tech Partner"



def extract_location(
    title: str,
    text: str = "",
    wanted_location: str = "",
    remote_only: bool = False,
    agent_data: dict[str, Any] | None = None,
) -> str:
    """Extract verified location from agent data, Markdown metadata, or body text."""
    if agent_data and agent_data.get("location"):
        candidate = str(agent_data["location"]).strip()
        if candidate and candidate.lower() not in ("not verified", "unknown"):
            return candidate

    if text:
        m_loc = re.search(r"##\s*Location\s*\n+([^\n#]+)", text, re.IGNORECASE)
        if m_loc:
            val = m_loc.group(1).strip()
            if val and len(val) < 60:
                return val

        m_loctype = re.search(r"##\s*Location Type\s*\n+([^\n#]+)", text, re.IGNORECASE)
        if m_loctype and "remote" in m_loctype.group(1).lower():
            return "Remote"

        m_inline = re.search(r"\bLocation:\s*([^\n,]{2,40})", text, re.IGNORECASE)
        if m_inline:
            return m_inline.group(1).strip()

    combined = (title + " " + (text[:1200] if text else "")).lower()
    if "remote" in combined:
        return "Remote"
    if wanted_location and wanted_location.lower() in combined:
        return wanted_location

    return "Remote" if remote_only else (wanted_location or "Flexible / Hybrid")


def extract_seniority(
    title: str,
    text: str = "",
    wanted_seniority: str | None = None,
    agent_data: dict[str, Any] | None = None,
) -> str | None:
    """Identify seniority level from title, text, or user preference."""
    if agent_data and agent_data.get("seniority"):
        candidate = str(agent_data["seniority"]).strip()
        if candidate:
            return candidate

    combined = (title + " " + (text[:600] if text else "")).lower()
    if any(w in combined for w in ("intern", "internship", "apprentice")):
        return "Intern"
    if any(w in combined for w in ("junior", "entry level", "entry-level", "associate")):
        return "Junior"
    if any(w in combined for w in ("lead", "staff", "principal", "director", "head of")):
        return "Lead / Staff"
    if any(w in combined for w in ("senior", "sr.", "sr ")):
        return "Senior"
    if "mid-level" in combined or "mid level" in combined:
        return "Mid-level"

    return wanted_seniority or "All levels"


def extract_description(
    text: str = "",
    snippet: str = "",
    agent_data: dict[str, Any] | None = None,
) -> str:
    """Extract informative description summary without boilerplate or nav clutter."""
    if agent_data and agent_data.get("description"):
        candidate = str(agent_data["description"]).strip()
        if candidate and len(candidate) > 20:
            return candidate[:240].strip() + ("..." if len(candidate) > 240 else "")

    if text:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for p in paragraphs:
            cleaned = re.sub(r"#+|\*+|_|\[.*?\]\(.*?\)", "", p).strip()
            if (
                len(cleaned) > 75
                and not any(
                    skip in cleaned.lower()
                    for skip in (
                        "apply for this job",
                        "cookie",
                        "javascript",
                        "location:",
                        "department:",
                        "submit your resume",
                        "skip to main",
                    )
                )
            ):
                return cleaned[:240].strip() + ("..." if len(cleaned) > 240 else "")

    if snippet:
        cleaned_snippet = re.sub(r"\s+", " ", snippet).strip()
        return cleaned_snippet[:240].strip() + ("..." if len(cleaned_snippet) > 240 else "")

    return "Role details, requirements, and full team context available on the direct application page."


def score_listing(
    job: JobListing,
    preferences: UserPreferences,
    full_text: str = "",
) -> float:
    score = 0.0
    title = _norm(job.title)
    description = _norm(job.description)
    content = _norm(full_text[:2000]) if full_text else description

    # Role terms in title or description
    role_terms = [term for term in re.split(r"\W+", _norm(preferences.role)) if len(term) > 2]
    if any(term in title for term in role_terms):
        score += 4.0
    elif any(term in content for term in role_terms):
        score += 2.0

    # User keywords
    for keyword in preferences.keywords:
        word = _norm(keyword)
        if not word:
            continue
        if word in title:
            score += 3.0
        elif word in content:
            score += 1.5

    # Location alignment
    wanted_loc = _norm(preferences.location)
    job_loc = _norm(job.location)
    if wanted_loc and (wanted_loc in job_loc or wanted_loc in title or wanted_loc in content):
        score += 3.0

    # Remote preference
    if preferences.remote_only and ("remote" in job_loc or "remote" in title or "remote" in content):
        score += 2.0

    # Seniority match
    if preferences.seniority:
        sen = _norm(preferences.seniority)
        if sen in _norm(job.seniority) or sen in title:
            score += 2.0

    # Live verification bonus
    if job.company and job.company != "Tech Partner":
        score += 1.0

    return round(score, 1)


def match_and_rank(
    candidates: list[dict[str, Any]],
    preferences: UserPreferences,
    fetched_contents: dict[str, dict[str, Any]] | None = None,
    agent_results: dict[str, dict[str, Any]] | None = None,
) -> list[JobListing]:
    fetched = fetched_contents or {}
    agents = agent_results or {}
    by_key: dict[tuple[str, str], JobListing] = {}

    for candidate in candidates:
        url = str(candidate.get("url") or "").strip()
        if not url:
            continue

        raw_title = str(candidate.get("title") or "Job Opening").strip()
        snippet = str(candidate.get("snippet") or "").strip()
        page_info = fetched.get(url, {})
        page_text = str(page_info.get("text") or "")
        page_title = str(page_info.get("title") or "") or raw_title
        agent_data = agents.get(url)

        # Title: prefer agent title, then page title if substantive, else raw title
        title = (
            (agent_data.get("title") if agent_data else None)
            or (page_title if len(page_title) > len(raw_title) else raw_title)
            or raw_title
        )
        title = re.sub(r"\s*[-|]\s*(?:LinkedIn.*|Workable.*|Indeed.*|Glassdoor.*)$", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s+", " ", title).strip()

        company = extract_company(title, url, text=page_text, agent_data=agent_data)
        location = extract_location(
            title,
            text=page_text,
            wanted_location=preferences.location,
            remote_only=preferences.remote_only,
            agent_data=agent_data,
        )
        seniority = extract_seniority(
            title,
            text=page_text,
            wanted_seniority=preferences.seniority,
            agent_data=agent_data,
        )
        description = extract_description(
            text=page_text,
            snippet=snippet,
            agent_data=agent_data,
        )

        source = (urlparse(url).hostname or "").removeprefix("www.")
        key = (_norm(title), _norm(company))
        if key in by_key:
            continue

        listing = JobListing(
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            posted_date=page_info.get("published_date"),
            seniority=seniority,
            source=source,
        )
        listing.match_score = score_listing(listing, preferences, full_text=page_text)
        by_key[key] = listing

    return sorted(
        by_key.values(),
        key=lambda job: (job.match_score, job.title.casefold()),
        reverse=True,
    )

