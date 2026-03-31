"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/base-client";
import {
  getCurrentUser,
  type CurrentUser,
  requestLocalDemoAccess,
  signInWithLocalAccount,
  signUpWithLocalAccount,
} from "@/lib/api/auth";
import { clearSessionToken, getSessionToken, setSessionToken } from "@/lib/auth/session";

type SessionStatus = "checking" | "signed_out" | "signed_in";
type AuthMode = "sign_in" | "sign_up" | "demo";

export interface LoginSupabaseConfig {
  supabaseUrl: string;
  supabasePublishableKey: string;
}

interface DemoLoginPanelProps {
  supabaseConfig?: LoginSupabaseConfig | null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return "Local demo login is disabled in the backend. Start FastAPI with ENABLE_LOCAL_DEMO_AUTH=true.";
    }
    if (error.status === 401) {
      return "The saved browser session is no longer valid. Sign in again to continue.";
    }
  }

  if (error instanceof Error) {
    return error.message;
  }
  return "Unable to enable local demo access right now.";
}

function getAuthErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Unable to complete the browser authentication request right now.";
}

function isConfiguredSupabaseAuth(config?: LoginSupabaseConfig | null): config is LoginSupabaseConfig {
  return Boolean(config?.supabaseUrl && config?.supabasePublishableKey);
}

export default function DemoLoginPanel({
  supabaseConfig = null,
}: DemoLoginPanelProps) {
  const router = useRouter();
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("checking");
  const [authMode, setAuthMode] = useState<AuthMode>("sign_in");
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  async function applyValidatedSession(
    accessToken: string,
    successMessage: string,
  ): Promise<void> {
    const user = await getCurrentUser({ accessToken });
    setSessionToken(accessToken);
    setCurrentUser(user);
    setSessionStatus("signed_in");
    setMessage(successMessage);
    setError(null);
  }

  useEffect(() => {
    let isActive = true;

    async function validateStoredSession(): Promise<void> {
      let token = getSessionToken();

      if (!token) {
        if (!isActive) {
          return;
        }
        setSessionStatus("signed_out");
        setCurrentUser(null);
        setMessage(null);
        return;
      }

      setSessionStatus("checking");
      setError(null);

      try {
        await applyValidatedSession(
          token,
          "Saved browser access is active and has been validated against the backend.",
        );
        if (!isActive) {
          return;
        }
      } catch {
        clearSessionToken();
        if (!isActive) {
          return;
        }
        setCurrentUser(null);
        setSessionStatus("signed_out");
        setMessage("Saved browser access expired or is invalid. Sign in again to continue.");
      }
    }

    void validateStoredSession();

    return () => {
      isActive = false;
    };
  }, []);

  async function handleEnableDemoAccess(): Promise<void> {
    setIsLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await requestLocalDemoAccess();
      await applyValidatedSession(
        response.access_token,
        `Local demo access is ready in this browser for ${response.email}.`,
      );
    } catch (requestError) {
      clearSessionToken();
      setCurrentUser(null);
      setSessionStatus("signed_out");
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleEmailPasswordAuth(): Promise<void> {
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    if (authMode === "sign_up" && password !== confirmPassword) {
      setError("Password confirmation does not match.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setMessage(null);

    try {
      const normalizedEmail = email.trim().toLowerCase();
      const response =
        authMode === "sign_up"
          ? await signUpWithLocalAccount({
              email: normalizedEmail,
              password,
            })
          : await signInWithLocalAccount({
              email: normalizedEmail,
              password,
            });

      await applyValidatedSession(
        response.access_token,
        authMode === "sign_up"
          ? `Account created successfully for ${response.email}.`
          : `Signed in successfully as ${response.email}.`,
      );
    } catch (authError) {
      clearSessionToken();
      setCurrentUser(null);
      setSessionStatus("signed_out");
      setError(getAuthErrorMessage(authError));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleClearAccess(): Promise<void> {
    clearSessionToken();
    setCurrentUser(null);
    setSessionStatus("signed_out");
    setError(null);
    setMessage("Saved browser access has been cleared.");
  }

  const hasStoredSession = sessionStatus === "signed_in";
  const isCheckingSession = sessionStatus === "checking";
  const hasBrowserAuth = isConfiguredSupabaseAuth(supabaseConfig);

  return (
    <section className="page-stack">
      <div className="login-layout">
        <div className="home-hero">
          <div className="home-hero__copy">
            <p className="eyebrow">Protected demo access</p>
            <h1>Login</h1>
            <p className="lead">
              Create a local thesis account or sign in with one that already exists.
              FastAPI issues the access token used by the protected MVP pages.
            </p>
            <ul className="auth-list">
              <li>
                <strong>Demo account</strong>
                <span>
                  <span className="mono">analyst@example.com</span> with the{" "}
                  <span className="mono">data_analyst</span> role and access to store 1.
                </span>
              </li>
              <li>
                <strong>Local account flow</strong>
                <span>
                  Signup and login are handled directly by FastAPI in this local thesis
                  environment, so the flow works even when Supabase is unreachable.
                </span>
              </li>
              <li>
                <strong>Local fallback</strong>
                <span>
                  If the environment is still in thesis-demo mode, FastAPI can issue a
                  scoped analyst token with <code className="mono">ENABLE_LOCAL_DEMO_AUTH=true</code>.
                </span>
              </li>
            </ul>
          </div>

          <aside className="home-hero__aside">
            <div className="home-status-card">
              <p className="eyebrow eyebrow--amber">Access path</p>
              <ul className="status-list">
                <li>
                  <strong>1. Create account</strong>
                  <span>Sign up once with email and password in the local FastAPI environment.</span>
                </li>
                <li>
                  <strong>2. Sign in</strong>
                  <span>Reuse the same credentials to get a validated access token in this browser.</span>
                </li>
                <li>
                  <strong>3. Open dashboard</strong>
                  <span>Validate store KPIs, sales history, and recent records.</span>
                </li>
                <li>
                  <strong>4. Open forecasts</strong>
                  <span>Show published forecast points, metrics, and warnings.</span>
                </li>
              </ul>
            </div>
          </aside>
        </div>

        <aside className="auth-card">
          <div className="auth-card__top">
            <span className="auth-chip">Access Workspace</span>
            <div className="section-copy">
              <h2>Sign in or create an account</h2>
              <p>
                The primary path now uses backend-owned local auth. If you only need
                the seeded analyst account, the demo helper remains available below.
              </p>
            </div>
          </div>

          <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              aria-label="Switch to sign in"
              className={authMode === "sign_in" ? "auth-mode-tab auth-mode-tab--active" : "auth-mode-tab"}
              onClick={() => {
                setAuthMode("sign_in");
                setError(null);
                setMessage(null);
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              aria-label="Switch to sign up"
              className={authMode === "sign_up" ? "auth-mode-tab auth-mode-tab--active" : "auth-mode-tab"}
              onClick={() => {
                setAuthMode("sign_up");
                setError(null);
                setMessage(null);
              }}
            >
              Sign up
            </button>
            <button
              type="button"
              aria-label="Switch to demo access"
              className={authMode === "demo" ? "auth-mode-tab auth-mode-tab--active" : "auth-mode-tab"}
              onClick={() => {
                setAuthMode("demo");
                setError(null);
                setMessage(null);
              }}
            >
              Demo access
            </button>
          </div>

          {authMode !== "demo" ? (
            <div className="auth-form" aria-label="Account authentication form">
              <div className="field-group">
                <label htmlFor="auth-email">Email</label>
                <input
                  id="auth-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                  }}
                  placeholder="you@example.com"
                />
              </div>

              <div className="field-group">
                <label htmlFor="auth-password">Password</label>
                <input
                  id="auth-password"
                  type="password"
                  autoComplete={authMode === "sign_in" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                  }}
                  placeholder="Enter your password"
                />
              </div>

              {authMode === "sign_up" ? (
                <div className="field-group">
                  <label htmlFor="auth-confirm-password">Confirm password</label>
                  <input
                    id="auth-confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                    }}
                    placeholder="Repeat your password"
                  />
                </div>
              ) : null}

              <div className="button-row">
                <button type="button" className="button" onClick={handleEmailPasswordAuth} disabled={isLoading}>
                  <span className="sr-only">
                    {authMode === "sign_up" ? "Submit sign up" : "Submit sign in"}
                  </span>
                  {isLoading
                    ? authMode === "sign_up"
                      ? "Creating account..."
                      : "Signing in..."
                    : authMode === "sign_up"
                      ? "Create account"
                      : "Sign in"}
                </button>
              </div>

              <div className="info-banner">
                FastAPI will create or validate the account, issue the access token,
                and the protected pages will reuse that token directly.
                {hasBrowserAuth ? " External Supabase settings are present, but they are not required for the local thesis login flow." : ""}
              </div>
            </div>
          ) : null}

          {authMode === "demo" ? (
            <div className="auth-form">
              <div className="section-copy">
                <h3>Local thesis demo path</h3>
                <p>
                  This stores a scoped analyst token in local storage so the protected
                  frontend pages can call the backend APIs.
                </p>
              </div>

              <div className="login-actions">
                <button type="button" className="button" onClick={handleEnableDemoAccess} disabled={isLoading}>
                  {isLoading
                    ? "Enabling local demo access..."
                    : hasStoredSession
                      ? "Refresh local demo access"
                      : "Use local analyst demo access"}
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => {
                    void handleClearAccess();
                  }}
                  disabled={isLoading || !hasStoredSession}
                >
                  Clear saved access
                </button>
              </div>
            </div>
          ) : hasStoredSession ? (
            <div className="button-row">
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  void handleClearAccess();
                }}
              >
                Sign out
              </button>
            </div>
          ) : null}

          {isCheckingSession ? (
            <div className="info-banner">
              Checking the saved browser session before enabling the protected demo pages.
            </div>
          ) : null}
          {message ? <div className="status-banner">{message}</div> : null}
          {error ? <div role="alert" className="error-banner">{error}</div> : null}

          {hasStoredSession ? (
            <div className="auth-card__details">
              <ul className="detail-list">
                <li>
                  <strong>Authenticated email</strong>
                  <span>{currentUser?.email ?? "No email returned"}</span>
                </li>
                <li>
                  <strong>Active role</strong>
                  <span className="mono">{currentUser?.role ?? "unknown"}</span>
                </li>
                <li>
                  <strong>Validation source</strong>
                  <span className="mono">GET /api/v1/auth/me</span>
                </li>
              </ul>

              <p className="muted">Protected pages:</p>
              <div className="link-grid">
                <Link href="/dashboard" className="link-card">
                  <span>
                    <strong>Open the dashboard</strong>
                    <span>Review KPI summaries and store-level history.</span>
                  </span>
                  <span>Go</span>
                </Link>
                <Link href="/forecasts" className="link-card">
                  <span>
                    <strong>Open the forecasts page</strong>
                    <span>Review the active published forecast for the accessible store.</span>
                  </span>
                  <span>Go</span>
                </Link>
              </div>

              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => {
                    router.push("/dashboard");
                  }}
                >
                  Continue to dashboard
                </button>
              </div>
            </div>
          ) : (
            <div className="info-banner">
              No active browser session is available yet. Use sign in, sign up, or the demo access helper above.
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
