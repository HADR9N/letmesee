import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { ArrowDownRight, ArrowUpRight, Check, Copy, ExternalLink, Loader2, MapPin, Search, ShieldCheck } from "lucide-react";
import { AuthDialog } from "./components/AuthDialog";

type Job = { title: string; company: string; location: string; url: string; description?: string | null; posted_date?: string | null; seniority?: string | null; match_score: number; source?: string | null };
type SearchResponse = { query: Record<string, unknown>; count: number; results: Job[]; stages: Record<string, string>; warning?: string | null };
type User = { id: number; email: string };
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const PRESETS = [
  { label: "Founding engineer", role: "Founding Fullstack Engineer", location: "Remote", keywords: "TypeScript, React, Next.js, Node.js", seniority: "Mid-level" },
  { label: "AI infrastructure", role: "AI Infrastructure Engineer", location: "San Francisco / Remote", keywords: "Python, PyTorch, GPU, CUDA, FastAPI", seniority: "Senior" },
  { label: "Product design", role: "Product Designer", location: "Remote", keywords: "Figma, Design Systems, CSS, React", seniority: "Mid-level" },
  { label: "Systems", role: "Backend Systems Engineer", location: "Remote", keywords: "Rust, Go, Distributed Systems, Raft", seniority: "Senior" },
  { label: "Early career", role: "Software Engineering Intern", location: "Remote", keywords: "Python, TypeScript, SQL", seniority: "Intern" },
];

export default function App() {
  const [role, setRole] = useState("Backend Engineer");
  const [location, setLocation] = useState("Remote");
  const [keywords, setKeywords] = useState("Python, FastAPI");
  const [seniority, setSeniority] = useState("Junior");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [filterSource, setFilterSource] = useState("all");
  const [warning, setWarning] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<unknown>(null);
  const [sandboxUrl, setSandboxUrl] = useState("");
  const [sandboxRunning, setSandboxRunning] = useState(false);
  const [sandboxOutput, setSandboxOutput] = useState<unknown>(null);
  const [sandboxError, setSandboxError] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [authOpen, setAuthOpen] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me").then((response) => response.json()).then((data) => setUser(data.user || null)).catch(() => setUser(null));
  }, []);

  const filteredJobs = useMemo(() => results.filter((job) => {
    const source = (job.source || job.url).toLowerCase();
    if (filterSource === "all") return true;
    if (filterSource === "other") return !["naukri", "linkedin", "indeed", "foundit"].some((board) => source.includes(board));
    return source.includes(filterSource);
  }), [results, filterSource]);
  const filters = ["all", "naukri", "linkedin", "indeed", "foundit", "other"];
  const host = (url: string) => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return "Company site"; } };

  async function executeSearch(event?: FormEvent) {
    event?.preventDefault(); setLoading(true); setError(""); setWarning(""); setSearched(true); setVerifyResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role: role.trim(), location: location.trim(), keywords: keywords.split(",").map((item) => item.trim()).filter(Boolean), seniority: seniority || null, remote_only: remoteOnly, page: 0 }) });
      const data = await response.json().catch(() => ({})) as Partial<SearchResponse> & { detail?: string };
      if (!response.ok) throw new Error(data.detail || `Search failed (${response.status}).`);
      const received = Array.isArray(data.results) ? data.results : [];
      setResults(received); setSelectedJob(received[0] || null); setWarning(data.warning || "");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Search failed. Check server status."); setResults([]); setSelectedJob(null); }
    finally { setLoading(false); }
  }

  function choosePreset(preset: typeof PRESETS[number]) { setRole(preset.role); setLocation(preset.location); setKeywords(preset.keywords); setSeniority(preset.seniority); setRemoteOnly(true); }

  async function verifySelected() {
    if (!selectedJob) return; setVerifyLoading(true); setVerifyResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/agent/extract`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: selectedJob.url, goal: "Extract verified official job title, hiring company name, primary location, seniority level, and core requirements." }) });
      if (!res.ok) {
        const fallback = await fetch(`${API_BASE}/api/fetch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ urls: [selectedJob.url] }) });
        if (!fallback.ok) throw new Error("Could not verify this listing.");
        const data = await fallback.json(); setVerifyResult(data.results?.[selectedJob.url] || data); return;
      }
      const data = await res.json(); setVerifyResult(data.result || data);
    } catch (caught) { setVerifyResult({ error: caught instanceof Error ? caught.message : "Verification failed." }); }
    finally { setVerifyLoading(false); }
  }

  async function runSandbox() {
    if (!sandboxUrl.trim()) return; setSandboxRunning(true); setSandboxError(""); setSandboxOutput(null);
    try { const res = await fetch(`${API_BASE}/api/fetch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ urls: [sandboxUrl.trim()] }) }); if (!res.ok) throw new Error(`Fetch failed (${res.status}).`); setSandboxOutput(await res.json()); }
    catch (caught) { setSandboxError(caught instanceof Error ? caught.message : "Verification request failed."); }
    finally { setSandboxRunning(false); }
  }

  async function copyLink() { if (!selectedJob) return; await navigator.clipboard.writeText(selectedJob.url); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
  }

  return <><main className="site-shell">
    <header className="top-nav"><a className="brand-mark" href="#top" aria-label="letmesee home">letmesee<span>®</span></a><div className="nav-right"><span className="nav-note">A clearer way to find your next role</span><a className="nav-anchor" href="#verify">Check a listing <ArrowUpRight size={15}/></a>{user ? <button className="auth-nav-button" onClick={signOut}>Sign out</button> : <button className="auth-nav-button" onClick={() => setAuthOpen(true)}>Sign in <ArrowUpRight size={14}/></button>}</div></header>
    <section className="hero" id="top"><div className="hero-copy"><span className="eyebrow"><span className="eyebrow-line"/> GOOD WORK, FOUND</span><h1>Find work<br/>worth <em>showing up for.</em></h1><p>Search real openings from the companies hiring. Choose what matters, then go straight to the source.</p></div><div className="hero-side"><div className="hero-index">01 <span> / SEARCH</span></div><p>Start with a role. Refine by place, experience, and the skills you bring.</p><ArrowDownRight className="hero-arrow" size={34}/></div></section>
    <section className="search-panel" aria-label="Job search"><form onSubmit={executeSearch}><div className="search-fields"><label className="field role-field"><span>WHAT DO YOU DO?</span><div><Search size={17}/><input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role or title" required/></div></label><label className="field"><span>WHERE?</span><div><MapPin size={17}/><input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City or remote" required/></div></label><label className="field seniority-field"><span>EXPERIENCE</span><select value={seniority} onChange={(e) => setSeniority(e.target.value)}><option value="">Any level</option><option value="Intern">Internship</option><option value="Junior">Junior</option><option value="Mid-level">Mid-level</option><option value="Senior">Senior</option><option value="Staff">Staff</option></select></label><button className="search-button" disabled={loading}>{loading ? <Loader2 className="spin" size={18}/> : <>Show me <ArrowUpRight size={18}/></>}</button></div><div className="search-extras"><label className="keywords-field"><span>SKILLS</span><input value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="Add skills, separated by commas"/></label><label className="remote-toggle"><input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)}/><span className="toggle-track"/><span>Remote friendly</span></label></div></form></section>
    <div className="suggestions"><span className="suggestion-label">A place to start</span>{PRESETS.map((preset) => <button key={preset.label} onClick={() => choosePreset(preset)}>{preset.label}<ArrowUpRight size={12}/></button>)}</div>
      <section className="results-section" aria-label="Job openings"><div className="results-heading"><div><span className="eyebrow"><span className="eyebrow-line"/> THE SHORTLIST</span><h2>{searched ? (filteredJobs.length ? `${filteredJobs.length} openings` : "No openings yet") : "Your next move"}</h2></div><div className="source-filters" aria-label="Filter by source">{filters.map((filter) => <button key={filter} className={filterSource === filter ? "active" : ""} onClick={() => setFilterSource(filter)}>{filter === "all" ? "All boards" : filter === "other" ? "Other boards" : filter[0].toUpperCase() + filter.slice(1)}</button>)}</div></div>
      {error && <p className="notice error-notice">{error}</p>}{warning && <p className="notice">{warning}</p>}
      {!searched && <div className="empty-state"><span className="empty-number">01—</span><div><h3>A good role starts with a good search.</h3><p>Tell us what you do and where you’d like to do it. We’ll bring back openings from company career pages.</p></div><button onClick={() => executeSearch()} disabled={loading}>Search for {role}<ArrowUpRight size={16}/></button></div>}
      {searched && !loading && filteredJobs.length === 0 && !error && <div className="empty-state"><span className="empty-number">∅</span><div><h3>Nothing in this search.</h3><p>Try a broader title, location, or skill set.</p></div><button onClick={() => { setRole("Software Engineer"); setSeniority(""); }}>Broaden search<ArrowUpRight size={16}/></button></div>}
      {loading && <div className="loading-state"><Loader2 className="spin"/> Looking for openings…</div>}
      {filteredJobs.length > 0 && <div className="job-layout"><div className="job-list">{filteredJobs.map((job, index) => <button key={`${job.url}-${index}`} className={`job-row ${selectedJob?.url === job.url ? "selected" : ""}`} onClick={() => { setSelectedJob(job); setVerifyResult(null); }}><span className="job-order">{String(index + 1).padStart(2, "0")}</span><span className="job-row-main"><span className="job-company">{job.company}<span className="source-dot"/> <span className="source-name">{host(job.url)}</span></span><strong>{job.title}</strong><span className="job-meta"><span><MapPin size={13}/>{job.location}</span>{job.seniority && <span>{job.seniority}</span>}{job.posted_date && <span>{job.posted_date}</span>}</span></span><ArrowUpRight className="row-arrow" size={18}/></button>)}</div>
      {selectedJob && <aside className="job-detail"><div className="detail-top"><span className="eyebrow"><ShieldCheck size={14}/> COMPANY LISTING</span><span className="detail-source">{host(selectedJob.url)}</span></div><p className="detail-company">{selectedJob.company}</p><h3>{selectedJob.title}</h3><p className="detail-location"><MapPin size={15}/>{selectedJob.location}{selectedJob.seniority ? ` · ${selectedJob.seniority}` : ""}</p>{selectedJob.description && <div className="detail-description"><p>{selectedJob.description}</p></div>}<div className="detail-actions"><a className="apply-link" href={selectedJob.url} target="_blank" rel="noopener noreferrer">View and apply <ExternalLink size={16}/></a><button className="icon-action" onClick={copyLink} aria-label="Copy listing link">{copied ? <Check size={17}/> : <Copy size={17}/>}</button><button className="verify-link" onClick={verifySelected} disabled={verifyLoading}>{verifyLoading ? <Loader2 className="spin" size={16}/> : <ShieldCheck size={16}/>} {verifyLoading ? "Checking" : "Verify details"}</button></div>{verifyResult !== null && <div className="verification-result"><div className="result-label">CHECK RESULT</div><pre>{JSON.stringify(verifyResult, null, 2)}</pre></div>}</aside>}</div>}
    </section>
    <section className="verify-section" id="verify"><div className="verify-intro"><span className="eyebrow"><span className="eyebrow-line"/> HAVE A LINK?</span><h2>Check a listing<br/><em>before you apply.</em></h2><p>Paste a company career page link to fetch its current details.</p></div><div className="verify-form"><label htmlFor="listing-url">Company listing URL</label><div className="verify-input"><input id="listing-url" value={sandboxUrl} onChange={(e) => setSandboxUrl(e.target.value)} placeholder="https://careers.company.com/role"/><button onClick={runSandbox} disabled={sandboxRunning || !sandboxUrl.trim()}>{sandboxRunning ? <Loader2 className="spin" size={17}/> : <>Check link <ArrowUpRight size={17}/></>}</button></div>{sandboxError && <p className="verify-error">{sandboxError}</p>}{sandboxOutput !== null && <pre className="verification-result sandbox-output">{JSON.stringify(sandboxOutput, null, 2)}</pre>}</div></section>
    <footer className="site-footer"><a className="brand-mark" href="#top">letmesee<span>®</span></a><span>Find the work that fits.</span><a href="#top">Back to top ↑</a></footer>
  </main>{authOpen && <AuthDialog onClose={() => setAuthOpen(false)} onAuthenticated={(signedInUser) => { setUser(signedInUser); setAuthOpen(false); }}/>}</>;
}
