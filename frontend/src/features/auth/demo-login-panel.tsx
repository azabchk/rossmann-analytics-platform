"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { requestLocalDemoAccess } from "@/lib/api/auth";
import { clearSessionToken, getSessionToken, setSessionToken } from "@/lib/auth/session";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unable to enable local demo access right now.";
}

export default function DemoLoginPanel() {
  const [hasStoredSession, setHasStoredSession] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getSessionToken()) {
      setHasStoredSession(true);
      setMessage("A saved browser session is already available for the protected demo pages.");
    }
  }, []);

  async function handleEnableDemoAccess(): Promise<void> {
    setIsLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await requestLocalDemoAccess();
      setSessionToken(response.access_token);
      setHasStoredSession(true);
      setMessage("Local demo access is ready in this browser. You can open the dashboard now.");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  function handleClearAccess(): void {
    clearSessionToken();
    setHasStoredSession(false);
    setError(null);
    setMessage("Saved browser access has been cleared.");
  }

  return (
    <section>
      <h1>Login</h1>
      <p>
        For local development, this page can request the seeded analyst demo token
        from FastAPI and store it in browser storage.
      </p>
      <p>
        Demo account: <strong>analyst@example.com</strong> with the{" "}
        <strong>data_analyst</strong> role and access to store 1.
      </p>
      <p>
        This helper is for local demo use only and does not replace a full Supabase
        browser login flow.
      </p>
      <p>Backend requirement: start FastAPI with <code>ENABLE_LOCAL_DEMO_AUTH=true</code>.</p>
      <p>
        <button type="button" onClick={handleEnableDemoAccess} disabled={isLoading}>
          {isLoading ? "Enabling local demo access..." : "Use local analyst demo access"}
        </button>
      </p>
      <p>
        <button type="button" onClick={handleClearAccess} disabled={isLoading}>
          Clear saved access
        </button>
      </p>
      {message ? <p>{message}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {hasStoredSession ? (
        <>
          <p>Protected pages:</p>
          <ul>
            <li>
              <Link href="/dashboard">Open the dashboard</Link>
            </li>
            <li>
              <Link href="/forecasts">Open the forecasts page</Link>
            </li>
          </ul>
        </>
      ) : null}
    </section>
  );
}
