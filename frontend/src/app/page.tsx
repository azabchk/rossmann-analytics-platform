import Link from "next/link";

export default function HomePage() {
  return (
    <section>
      <h1>Analytical Platform for an Online Store</h1>
      <p>
        This frontend is a thin presentation shell. All protected business data
        and business rules remain behind the FastAPI backend.
      </p>
      <p>
        Current MVP status: dashboard and forecast pages consume the FastAPI
        backend for KPI and published forecast data.
      </p>
      <p>
        <Link href="/dashboard">Open the dashboard</Link>
      </p>
      <p>
        <Link href="/forecasts">Open the forecasts page</Link>
      </p>
    </section>
  );
}
