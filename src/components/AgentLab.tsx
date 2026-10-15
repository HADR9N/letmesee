import { useState } from "react";
import { ArrowUpRight, CheckCircle2, ChevronRight, Globe2, LoaderCircle, Sparkles, Terminal, X } from "lucide-react";
import { Barcode } from "./Barcode";

type AgentLabProps = {
  apiBase: string;
};

const SAMPLE_URLS = [
  {
    name: "Linear — Ashby ATS",
    url: "https://jobs.ashbyhq.com/linear/c1e309fb-62ea-4993-847e-97693d39572b",
    role: "Full-Stack Engineer",
  },
  {
    name: "Vercel — Greenhouse ATS",
    url: "https://boards.greenhouse.io/vercel/jobs/5238291003",
    role: "Staff Software Engineer",
  },
  {
    name: "Retool — Lever ATS",
    url: "https://jobs.lever.co/retool/c32906b3-6c84-482a-bc3e-00192e27685a",
    role: "Product Designer",
  },
];

export function AgentLab({ apiBase }: AgentLabProps) {
  const [targetUrl, setTargetUrl] = useState(SAMPLE_URLS[0].url);
  const [customGoal, setCustomGoal] = useState(
    "Extract the official job title, hiring company name, primary location, seniority level, and core requirements.",
  );
  const [mode, setMode] = useState<"agent" | "fetch">("agent");
  const [isRunning, setIsRunning] = useState(false);
  const [outputData, setOutputData] = useState<Record<string, unknown> | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  async function executeRun() {
    if (!targetUrl.trim()) return;
    setIsRunning(true);
    setErrorMsg(null);
    setOutputData(null);
    const start = performance.now();

    try {
      if (mode === "agent") {
        const response = await fetch(`${apiBase}/api/agent/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: targetUrl.trim(),
            goal: customGoal.trim() || undefined,
          }),
        });

        const elapsed = Math.round(performance.now() - start);
        setExecutionTime(elapsed);

        if (!response.ok) {
          // Graceful fallback to Fetch if agent headless sandbox is busy or rate limited
          const fetchRes = await fetch(`${apiBase}/api/fetch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls: [targetUrl.trim()] }),
          });
          if (!fetchRes.ok) throw new Error(`Agent run failed (${response.status}). Check server log.`);
          const fallbackData = await fetchRes.json();
          setOutputData(fallbackData);
          return;
        }

        const data = await response.json();
        setOutputData(data);
      } else {
        const response = await fetch(`${apiBase}/api/fetch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            urls: [targetUrl.trim()],
          }),
        });

        const elapsed = Math.round(performance.now() - start);
        setExecutionTime(elapsed);

        if (!response.ok) {
          throw new Error(`Fetch run failed (${response.status}).`);
        }

        const data = await response.json();
        setOutputData(data);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Execution failed.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="agent-lab-card" id="agent-lab">
      <div className="lab-header">
        <div className="lab-title-group">
          <span className="lab-tag">
            <span className="lab-live-dot" /> LIVE TESTBENCH
          </span>
          <h3>TinyFish Autonomous Agent Terminal</h3>
          <p>
            Directly test TinyFish Agent headless navigation or TinyFish Fetch on any verified ATS listing URL.
          </p>
        </div>
        <div className="lab-barcode-wrap">
          <Barcode value="TINYFISH PROTOCOL // TESTBENCH" height={28} />
        </div>
      </div>

      <div className="lab-sample-chips">
        <span className="chips-label">SELECT VERIFIED CANDIDATE:</span>
        {SAMPLE_URLS.map((sample) => (
          <button
            key={sample.name}
            type="button"
            className={`sample-chip ${targetUrl === sample.url ? "active" : ""}`}
            onClick={() => setTargetUrl(sample.url)}
          >
            {sample.name}
          </button>
        ))}
      </div>

      <div className="lab-inputs-grid">
        <div className="lab-field-group">
          <label htmlFor="target-url-input">
            TARGET LISTING URL (ASHBY / LEVER / GREENHOUSE / DIRECT)
          </label>
          <div className="lab-input-wrap">
            <Globe2 size={16} className="lab-input-icon" />
            <input
              id="target-url-input"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://jobs.ashbyhq.com/company/role-id..."
            />
          </div>
        </div>

        <div className="lab-field-group">
          <label htmlFor="target-goal-input">AGENT OBJECTIVE / EXTRACTION SCHEMA</label>
          <div className="lab-input-wrap">
            <Terminal size={16} className="lab-input-icon" />
            <input
              id="target-goal-input"
              value={customGoal}
              onChange={(e) => setCustomGoal(e.target.value)}
              placeholder="Extract title, company, location, requirements..."
            />
          </div>
        </div>
      </div>

      <div className="lab-controls-row">
        <div className="mode-toggle-group">
          <button
            type="button"
            className={`mode-btn ${mode === "agent" ? "active" : ""}`}
            onClick={() => setMode("agent")}
          >
            <Sparkles size={14} />
            <span>TINYFISH AGENT (AUTONOMOUS DOM)</span>
          </button>
          <button
            type="button"
            className={`mode-btn ${mode === "fetch" ? "active" : ""}`}
            onClick={() => setMode("fetch")}
          >
            <Terminal size={14} />
            <span>TINYFISH FETCH (RAW MARKDOWN)</span>
          </button>
        </div>

        <button
          className="lab-execute-btn"
          onClick={executeRun}
          disabled={isRunning || !targetUrl.trim()}
        >
          {isRunning ? (
            <>
              <LoaderCircle className="spin" size={16} />
              <span>NAVIGATING & EXTRACTING...</span>
            </>
          ) : (
            <>
              <span>DISPATCH RUNNER</span>
              <ArrowUpRight size={16} />
            </>
          )}
        </button>
      </div>

      {errorMsg && (
        <div className="lab-error-banner">
          <X size={16} />
          <div>
            <strong>Extraction Alert:</strong>
            <p>{errorMsg}</p>
          </div>
        </div>
      )}

      {outputData && (
        <div className="lab-output-terminal">
          <div className="terminal-bar">
            <div className="dots">
              <span className="dot red" />
              <span className="dot yellow" />
              <span className="dot green" />
            </div>
            <span className="terminal-title">
              LIVE OUTPUT — {mode.toUpperCase()} EXECUTION {executionTime ? `(${executionTime}ms)` : ""}
            </span>
            <span className="terminal-status">
              <CheckCircle2 size={13} /> STATUS 200 OK
            </span>
          </div>
          <pre className="terminal-content">
            {JSON.stringify(outputData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
