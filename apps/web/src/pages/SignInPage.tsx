import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/authState";

export function SignInPage() {
  const { signIn, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("researcher@runscope.dev");
  const [password, setPassword] = useState("ResearcherDemo123!");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/overview" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await signIn(email, password);
      const from = (location.state as { from?: string } | null)?.from ?? "/overview";
      navigate(from, { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sign in failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="sign-in-title">
        <div className="auth-intro">
          <p className="eyebrow">Trusted CPU workloads</p>
          <h1 id="sign-in-title">Sign in to RunScope</h1>
          <p>
            Create experiments, submit registered training templates, and inspect
            durable logs, metrics, and artifacts.
          </p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />
          {error ? (
            <div className="form-error" role="alert">
              {error}
            </div>
          ) : null}
          <button className="button button-primary" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
          <p className="form-help">
            Local demonstration credentials are prefilled. This is not an enterprise
            identity system.
          </p>
        </form>
      </section>
    </main>
  );
}
