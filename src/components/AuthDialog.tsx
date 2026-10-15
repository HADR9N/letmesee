import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ArrowUpRight, Loader2, X } from "lucide-react";

type User = { id: number; email: string };
type AuthDialogProps = { onClose: () => void; onAuthenticated: (user: User) => void };

export function AuthDialog({ onClose, onAuthenticated }: AuthDialogProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) { if (event.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (mode === "register" && password !== confirmPassword) { setError("Those passwords don’t match."); return; }
    setLoading(true);
    try {
      const response = await fetch(`/api/auth/${mode === "register" ? "register" : "login"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Couldn’t sign you in. Try again.");
      onAuthenticated(data.user as User);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn’t connect. Try again.");
    } finally { setLoading(false); }
  }

  return <div className="auth-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button className="auth-close" onClick={onClose} aria-label="Close sign in"><X size={18}/></button>
      <div className="auth-art"><a href="#top" className="auth-brand">letmesee<span>®</span></a><div className="auth-art-copy"><span className="auth-overline">A LITTLE MORE FOCUS</span><h2>Good work<br/>is out there.</h2><p>Make a little space for your next move.</p></div><span className="auth-art-foot">A thoughtful next step starts here.</span></div>
      <div className="auth-form-side"><div className="auth-form-content"><span className="auth-overline">YOUR JOB SEARCH, KEPT</span><h1 id="auth-title">{mode === "login" ? "Welcome back." : "Make it yours."}</h1><p className="auth-lede">{mode === "login" ? "Sign in to pick up where you left off." : "Create an account to keep your search close."}</p>
        <form className="auth-form" onSubmit={submit}>
          <label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required maxLength={254}/></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={8} maxLength={128}/></label>
          {mode === "register" && <label>Confirm password<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Type it once more" autoComplete="new-password" required minLength={8} maxLength={128}/></label>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading}>{loading ? <Loader2 size={17} className="spin"/> : <>{mode === "login" ? "Sign in" : "Create account"}<ArrowUpRight size={17}/></>}</button>
        </form>
        <p className="auth-switch">{mode === "login" ? "New to letmesee?" : "Already have an account?"}<button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}> {mode === "login" ? "Create an account" : "Sign in"}</button></p>
        <p className="auth-privacy">Your account stays yours. We’ll only use your email to sign you in.</p>
      </div></div>
    </section>
  </div>;
}
