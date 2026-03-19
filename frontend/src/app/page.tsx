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
        Current phase status: shared shell, authentication entry point, and API
        client scaffolding only.
      </p>
      <p>
        <Link href="/login">Go to login placeholder</Link>
      </p>
    </section>
  );
}
