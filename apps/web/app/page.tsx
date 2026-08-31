import AuthPanel from "./components/AuthPanel";

export const dynamic = "force-dynamic";

type HealthResponse = {
  ok: boolean;
  service: string;
};

async function getHealth(
  apiBaseUrl: string
): Promise<HealthResponse | null> {
  if (!apiBaseUrl) {
    return null;
  }

  try {
    const response = await fetch(
      `${apiBaseUrl}/health`,
      {
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as HealthResponse;
  } catch (error) {
    console.error(
      "MIRANOAH API health check failed:",
      error
    );

    return null;
  }
}

export default async function Home() {
  const apiBaseUrl =
    process.env.API_BASE_URL ?? "";

  const health = await getHealth(
    apiBaseUrl
  );

  const connected =
    health?.ok === true;

  const cards = [
    [
      "API STATUS",
      connected ? "ONLINE" : "OFFLINE",
      connected
        ? `Connected to ${health?.service}`
        : "Backend connection failed",
    ],
    [
      "ACTIVE PROJECTS",
      "—",
      "Data connection pending",
    ],
    [
      "OPEN TASKS",
      "—",
      "Data connection pending",
    ],
    [
      "HIGH RISK",
      "—",
      "Data connection pending",
    ],
  ];

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          AI PMO / COMMAND CENTER
        </div>

        <AuthPanel
          apiBaseUrl={apiBaseUrl}
        />
      </header>

      <section className="hero">
        <h1>MIRANOAH</h1>

        <p className="tagline">
          すべてを見渡し、一つも取りこぼさない。
          Slackから仕事を理解し、組織全体のタスク・期限・Todo・リスクを統合する。
        </p>
      </section>

      <div className="grid">
        {cards.map(
          ([label, value, status]) => (
            <div
              className="card"
              key={label}
            >
              <span>{label}</span>

              <strong>{value}</strong>

              <div className="status">
                {status}
              </div>
            </div>
          )
        )}
      </div>
    </main>
  );
}
