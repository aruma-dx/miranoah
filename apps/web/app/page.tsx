type HealthResponse = {
  ok: boolean;
  service: string;
};

async function getHealth(): Promise<HealthResponse | null> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return null;
  }

  try {
    const response = await fetch(`${apiBaseUrl}/health`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();
  const connected = health?.ok === true;

  const cards = [
    ["API STATUS", connected ? "ONLINE" : "OFFLINE"],
    ["ACTIVE PROJECTS", "—"],
    ["OPEN TASKS", "—"],
    ["HIGH RISK", "—"],
  ];

  return (
    <main>
      <div className="brand">AI PMO / COMMAND CENTER</div>

      <h1>MIRANOAH</h1>

      <p className="tagline">
        すべてを見渡し、一つも取りこぼさない。
        Slackから仕事を理解し、組織全体のタスク・期限・Todo・リスクを統合する。
      </p>

      <div className="grid">
        {cards.map(([label, value]) => (
          <div className="card" key={label}>
            <span>{label}</span>

            <strong>{value}</strong>

            <div className="status">
              {label === "API STATUS"
                ? connected
                  ? `Connected to ${health?.service}`
                  : "Backend connection failed"
                : "Data connection pending"}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
