from __future__ import annotations

import concurrent.futures
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from src.config import UserPreferences, get_api_key
from src.auth import SESSION_TTL, create_account, end_session, find_session, sign_in
from src.matcher import JobListing, match_and_rank
from src.scraper import discover_job_urls, fetch_job_contents, run_agent_extraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("letmesee")

app = FastAPI(
    title="letmesee API",
    version="0.3.0",
    description="TinyFish-powered live job and internship discovery using Search, Fetch, and Agent.",
)

origins_env = os.getenv(
    "LETMESEE_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    seniority: str | None = Field(default=None, max_length=60)
    remote_only: bool = False
    page: int = Field(default=0, ge=0, le=10)


class SearchResponse(BaseModel):
    query: dict[str, Any]
    count: int
    results: list[JobListing]
    stages: dict[str, str]
    warning: str | None = None


class AgentExtractRequest(BaseModel):
    url: str
    goal: str | None = None


class FetchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=10)
    purpose: str | None = None


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="letmesee_session",
        value=token,
        max_age=SESSION_TTL,
        httponly=True,
        secure=os.getenv("LETMESEE_COOKIE_SECURE", "true" if os.getenv("VERCEL") == "1" else "false").lower() == "true",
        samesite="lax",
        path="/",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "letmesee-api"}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    return {"user": find_session(request.cookies.get("letmesee_session"))}


@app.post("/api/auth/register")
def auth_register(payload: AuthRequest, response: Response) -> dict[str, Any]:
    try:
        user, token = create_account(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {"user": user}


@app.post("/api/auth/login")
def auth_login(payload: AuthRequest, response: Response) -> dict[str, Any]:
    try:
        user, token = sign_in(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {"user": user}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, bool]:
    end_session(request.cookies.get("letmesee_session"))
    response.delete_cookie("letmesee_session", path="/", httponly=True, samesite="lax")
    return {"ok": True}


@app.post("/api/search", response_model=SearchResponse)
def search_jobs(request: SearchRequest) -> SearchResponse:
    try:
        get_api_key()
        preferences = UserPreferences(
            role=request.role,
            location=request.location,
            keywords=request.keywords,
            seniority=request.seniority,
            remote_only=request.remote_only,
        )

        # Stage 1: Discovery via TinyFish Search
        candidates = discover_job_urls(preferences, page=request.page)
        candidate_urls = [c["url"] for c in candidates][:8]

        # Stage 2: Live Content Retrieval via TinyFish Fetch
        fetched_contents: dict[str, dict[str, Any]] = {}
        if candidate_urls:
            fetched_contents = fetch_job_contents(candidate_urls)

        # Stage 3: Autonomous Browser Verification via TinyFish Agent (fast pass on top URL)
        agent_results: dict[str, dict[str, Any]] = {}
        if candidate_urls:
            top_url = candidate_urls[0]
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    agent_future = executor.submit(run_agent_extraction, top_url)
                    extracted = agent_future.result(timeout=10.0)
                    if extracted:
                        agent_results[top_url] = extracted
            except (concurrent.futures.TimeoutError, Exception) as exc:
                logger.info("Agent quick pass completed with fallback to Fetch: %s", exc)

        # Stage 4: Multi-factor Matching and Ranking
        ranked = match_and_rank(
            candidates,
            preferences,
            fetched_contents=fetched_contents,
            agent_results=agent_results,
        )

        return SearchResponse(
            query=preferences.model_dump(),
            count=len(ranked),
            results=ranked,
            stages={
                "discovery": "complete",
                "fetch": "complete",
                "agent": "complete",
                "matching": "complete",
            },
            warning=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("Search integration failed: %s", exc)
        message = str(exc)
        status = 503 if "API key is missing" in message else 502
        raise HTTPException(status_code=status, detail=message) from exc
    except Exception as exc:
        logger.exception("Unexpected search failure")
        raise HTTPException(
            status_code=502,
            detail=f"Search failed ({type(exc).__name__}). Check server logs.",
        ) from exc


@app.post("/api/agent/extract")
def agent_extract(request: AgentExtractRequest) -> dict[str, Any]:
    """Dedicated endpoint to test TinyFish Agent extraction on any target job listing."""
    try:
        get_api_key()
        result = run_agent_extraction(
            url=request.url,
            goal=request.goal or "Extract the official job title, hiring company name, location, seniority, and brief description.",
        )
        if not result:
            raise HTTPException(status_code=502, detail="TinyFish Agent failed to extract structured data.")
        return {"status": "ok", "url": request.url, "result": result}
    except Exception as exc:
        logger.exception("Agent extraction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/fetch")
def fetch_listings(request: FetchRequest) -> dict[str, Any]:
    """Dedicated endpoint to test TinyFish Fetch content extraction on target URLs."""
    try:
        get_api_key()
        results = fetch_job_contents(request.urls)
        return {"status": "ok", "count": len(results), "results": results}
    except Exception as exc:
        logger.exception("Fetch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

