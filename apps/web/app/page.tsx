import AuthPanel from "./components/AuthPanel";
import MiranoahDashboard from "./components/MiranoahDashboard";

export const dynamic =
  "force-dynamic";

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

    return (
      await response.json()
    ) as HealthResponse;
  } catch {
    return null;
  }
}

export default async function Home() {
  const apiBaseUrl =
    process.env.API_BASE_URL ?? "";

  const health =
    await getHealth(apiBaseUrl);

  return (
    <main>
      <header className="topbar">
        <div>
          <div className="brand">
            MIRANOAH
          </div>

          <div className="brand-sub">
            AI PMO / COMMAND CENTER
          </div>
        </div>

        <div className="topbar-right">
          <div
            className={
              health?.ok
                ? "api-indicator online"
                : "api-indicator offline"
            }
          >
            <span />

            API{" "}
            {health?.ok
              ? "ONLINE"
              : "OFFLINE"}
          </div>

          <AuthPanel
            apiBaseUrl={apiBaseUrl}
          />
        </div>
      </header>

      <section className="hero compact">
        <div className="hero-eyebrow">
          ORGANIZATIONAL INTELLIGENCE
        </div>

        <h1>
          MIRANOAH
        </h1>

        <p className="tagline">
          Slackから仕事を理解し、
          Project・Task・期限・リスクを
          一つの場所で管理するAI PMO。
        </p>
      </section>

      <MiranoahDashboard
        apiBaseUrl={apiBaseUrl}
      />
    </main>
  );
}
