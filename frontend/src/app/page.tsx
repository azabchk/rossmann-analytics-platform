import Link from "next/link";

export default function HomePage() {
  return (
    <section className="page-stack home-grid">
      <div className="home-hero">
        <div className="home-hero__copy">
          <p className="eyebrow">Retail Analytics MVP</p>
          <h1>Operational sales visibility and forecast publishing in one controlled surface.</h1>
          <p className="lead">
            This frontend stays intentionally thin. Store access, KPI aggregation,
            forecast publication, and authorization remain behind the FastAPI
            backend so the demo reflects the real system boundary.
          </p>

          <div className="hero-actions">
            <Link href="/dashboard" className="button">
              Open the dashboard
            </Link>
            <Link href="/forecasts" className="button-secondary">
              Review forecasts
            </Link>
            <Link href="/login" className="button-ghost">
              Enable local demo access
            </Link>
          </div>

          <div className="hero-metrics">
            <article className="hero-card">
              <strong>FastAPI</strong>
              <p>Protected KPI and forecast endpoints are the only business boundary.</p>
            </article>
            <article className="hero-card">
              <strong>Dashboard</strong>
              <p>Accessible stores, sales history, and KPI summaries for demo walkthroughs.</p>
            </article>
            <article className="hero-card">
              <strong>Forecasts</strong>
              <p>Published model outputs with confidence bounds and warning states.</p>
            </article>
          </div>
        </div>

        <aside className="home-hero__aside">
          <div className="home-status-card">
            <p className="eyebrow eyebrow--amber">Current state</p>
            <ul className="status-list">
              <li>
                <strong>Demo path is API-driven</strong>
                <span>Frontend reads only from the backend, not directly from Supabase.</span>
              </li>
              <li>
                <strong>Forecasting is integrated</strong>
                <span>Published forecast results and model metadata are available in the UI.</span>
              </li>
              <li>
                <strong>Local access is explicit</strong>
                <span>Use the login helper to request the seeded analyst token for local demos.</span>
              </li>
            </ul>
          </div>

          <div className="hero-note">
            Thesis-ready direction: backend-first analytics, presentation-first frontend.
          </div>
        </aside>
      </div>

      <div className="home-feature-grid">
        <article className="home-feature">
          <h2>Store performance</h2>
          <p>Review daily KPI history for accessible stores with date filters and recent records.</p>
        </article>
        <article className="home-feature">
          <h2>Forecast confidence</h2>
          <p>Inspect published model windows, prediction bands, and accuracy metrics in one view.</p>
        </article>
        <article className="home-feature">
          <h2>Demo workflow</h2>
          <p>Login locally, open the dashboard, then move to the forecast page for the thesis walkthrough.</p>
        </article>
      </div>
    </section>
  );
}
