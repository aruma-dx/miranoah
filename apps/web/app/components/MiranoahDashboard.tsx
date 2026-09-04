"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

type Props = {
  apiBaseUrl: string;
};

type AuthUser = {
  id: string;
  display_name: string;
  email: string | null;
  workspace_role:
    | "ADMIN"
    | "MANAGER"
    | "PLAYER";
};

type DashboardSummary = {
  active_projects: number;
  open_tasks: number;
  overdue: number;
  high_risk: number;
};

type Project = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  health: string;
  priority: string;
  progress: number;
  due_at: string | null;
};

type Task = {
  id: string;
  project_id: string | null;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  due_at: string | null;
  progress: number;
  risk_level: string;
};

type Team = {
  id: string;
  name: string;
  description: string | null;
};

const TASK_STATUSES = [
  "NOT_STARTED",
  "IN_PROGRESS",
  "WAITING_REVIEW",
  "WAITING_INTERNAL",
  "WAITING_EXTERNAL",
  "BLOCKED",
  "ON_HOLD",
  "DONE",
  "CANCELLED",
];

function statusLabel(
  status: string
) {
  const labels: Record<
    string,
    string
  > = {
    NOT_STARTED: "未着手",
    IN_PROGRESS: "進行中",
    WAITING_REVIEW: "レビュー待ち",
    WAITING_INTERNAL: "社内待ち",
    WAITING_EXTERNAL: "社外待ち",
    BLOCKED: "ブロック",
    ON_HOLD: "保留",
    DONE: "完了",
    CANCELLED: "キャンセル",
    CANDIDATE: "候補",
  };

  return labels[status] ?? status;
}

function dateLabel(
  value: string | null
) {
  if (!value) {
    return "期限なし";
  }

  return new Intl.DateTimeFormat(
    "ja-JP",
    {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(new Date(value));
}

export default function MiranoahDashboard({
  apiBaseUrl,
}: Props) {
  const [user, setUser] =
    useState<AuthUser | null>(null);

  const [summary, setSummary] =
    useState<DashboardSummary | null>(
      null
    );

  const [projects, setProjects] =
    useState<Project[]>([]);

  const [tasks, setTasks] =
    useState<Task[]>([]);

  const [teams, setTeams] =
    useState<Team[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [projectName, setProjectName] =
    useState("");

  const [
    projectDescription,
    setProjectDescription,
  ] = useState("");

  const [taskTitle, setTaskTitle] =
    useState("");

  const [
    taskProjectId,
    setTaskProjectId,
  ] = useState("");

  const [creatingProject, setCreatingProject] =
    useState(false);

  const [creatingTask, setCreatingTask] =
    useState(false);

  const apiFetch = useCallback(
    async (
      path: string,
      options?: RequestInit
    ) => {
      const response = await fetch(
        `${apiBaseUrl}${path}`,
        {
          ...options,
          credentials: "include",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            ...(options?.headers ?? {}),
          },
        }
      );

      return response;
    },
    [apiBaseUrl]
  );

  const loadData = useCallback(
    async () => {
      setError(null);

      try {
        const meResponse =
          await apiFetch(
            "/api/v1/auth/me"
          );

        if (!meResponse.ok) {
          setUser(null);
          setLoading(false);
          return;
        }

        const me =
          (await meResponse.json()) as AuthUser;

        setUser(me);

        const [
          summaryResponse,
          projectsResponse,
          tasksResponse,
          teamsResponse,
        ] = await Promise.all([
          apiFetch(
            "/api/v1/dashboard/summary"
          ),
          apiFetch(
            "/api/v1/projects"
          ),
          apiFetch(
            "/api/v1/tasks?limit=200"
          ),
          apiFetch(
            "/api/v1/teams"
          ),
        ]);

        if (
          !summaryResponse.ok ||
          !projectsResponse.ok ||
          !tasksResponse.ok ||
          !teamsResponse.ok
        ) {
          throw new Error(
            "MIRANOAHのデータ取得に失敗しました。"
          );
        }

        setSummary(
          await summaryResponse.json()
        );

        setProjects(
          await projectsResponse.json()
        );

        setTasks(
          await tasksResponse.json()
        );

        setTeams(
          await teamsResponse.json()
        );
      } catch (err) {
        console.error(err);

        setError(
          "データの取得中にエラーが発生しました。"
        );
      } finally {
        setLoading(false);
      }
    },
    [apiFetch]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function createProject(
    event: FormEvent
  ) {
    event.preventDefault();

    if (!projectName.trim()) {
      return;
    }

    setCreatingProject(true);
    setError(null);

    try {
      const response = await apiFetch(
        "/api/v1/projects",
        {
          method: "POST",
          body: JSON.stringify({
            name: projectName.trim(),
            description:
              projectDescription.trim() ||
              null,
            priority: "MEDIUM",
          }),
        }
      );

      if (!response.ok) {
        const body =
          await response.json().catch(
            () => null
          );

        throw new Error(
          body?.detail ??
            "Projectの作成に失敗しました。"
        );
      }

      setProjectName("");
      setProjectDescription("");

      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Projectの作成に失敗しました。"
      );
    } finally {
      setCreatingProject(false);
    }
  }

  async function createTask(
    event: FormEvent
  ) {
    event.preventDefault();

    if (!taskTitle.trim()) {
      return;
    }

    setCreatingTask(true);
    setError(null);

    try {
      const response = await apiFetch(
        "/api/v1/tasks",
        {
          method: "POST",
          body: JSON.stringify({
            title: taskTitle.trim(),
            project_id:
              taskProjectId || null,
            priority: "MEDIUM",
          }),
        }
      );

      if (!response.ok) {
        const body =
          await response.json().catch(
            () => null
          );

        throw new Error(
          body?.detail ??
            "Taskの作成に失敗しました。"
        );
      }

      setTaskTitle("");
      setTaskProjectId("");

      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Taskの作成に失敗しました。"
      );
    } finally {
      setCreatingTask(false);
    }
  }

  async function updateTaskStatus(
    taskId: string,
    status: string
  ) {
    setError(null);

    const response = await apiFetch(
      `/api/v1/tasks/${taskId}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          status,
        }),
      }
    );

    if (!response.ok) {
      const body =
        await response.json().catch(
          () => null
        );

      setError(
        body?.detail ??
          "Taskの更新に失敗しました。"
      );

      return;
    }

    await loadData();
  }

  if (loading) {
    return (
      <section className="loading-screen">
        MIRANOAHを読み込んでいます...
      </section>
    );
  }

  if (!user) {
    return (
      <section className="login-gate">
        <div className="section-kicker">
          AUTHENTICATION REQUIRED
        </div>

        <h2>
          Googleログイン後、
          MIRANOAHを利用できます。
        </h2>

        <p>
          右上の「Googleでログイン」から
          ログインしてください。
        </p>
      </section>
    );
  }

  return (
    <>
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <section className="welcome-row">
        <div>
          <div className="section-kicker">
            COMMAND CENTER
          </div>

          <h2>
            {user.display_name}
          </h2>

          <p>
            組織のProject・Task・Teamを
            一つの画面から確認できます。
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={loadData}
        >
          更新
        </button>
      </section>

      <section className="metrics-grid">
        <MetricCard
          label="ACTIVE PROJECTS"
          value={
            summary?.active_projects ?? 0
          }
        />

        <MetricCard
          label="OPEN TASKS"
          value={
            summary?.open_tasks ?? 0
          }
        />

        <MetricCard
          label="OVERDUE"
          value={
            summary?.overdue ?? 0
          }
          danger={
            (summary?.overdue ?? 0) > 0
          }
        />

        <MetricCard
          label="HIGH RISK"
          value={
            summary?.high_risk ?? 0
          }
          danger={
            (summary?.high_risk ?? 0) > 0
          }
        />
      </section>

      <section className="workspace-grid">
        <div className="panel">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">
                PROJECTS
              </div>

              <h3>
                Project
              </h3>
            </div>

            <span className="count-pill">
              {projects.length}
            </span>
          </div>

          <form
            className="quick-form"
            onSubmit={createProject}
          >
            <input
              value={projectName}
              onChange={(event) =>
                setProjectName(
                  event.target.value
                )
              }
              placeholder="Project名"
            />

            <input
              value={projectDescription}
              onChange={(event) =>
                setProjectDescription(
                  event.target.value
                )
              }
              placeholder="概要（任意）"
            />

            <button
              disabled={creatingProject}
            >
              {creatingProject
                ? "作成中..."
                : "Projectを作成"}
            </button>
          </form>

          <div className="list">
            {projects.length === 0 && (
              <EmptyState text="Projectはまだありません。" />
            )}

            {projects.map((project) => (
              <article
                className="list-item"
                key={project.id}
              >
                <div className="item-main">
                  <strong>
                    {project.name}
                  </strong>

                  <span>
                    {project.description ??
                      "説明なし"}
                  </span>
                </div>

                <div className="item-meta">
                  <span
                    className="status-badge"
                  >
                    {project.status}
                  </span>

                  <span>
                    {project.progress}%
                  </span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="panel task-panel">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">
                TASKS
              </div>

              <h3>
                Task
              </h3>
            </div>

            <span className="count-pill">
              {tasks.length}
            </span>
          </div>

          <form
            className="quick-form task-form"
            onSubmit={createTask}
          >
            <input
              value={taskTitle}
              onChange={(event) =>
                setTaskTitle(
                  event.target.value
                )
              }
              placeholder="Task名"
            />

            <select
              value={taskProjectId}
              onChange={(event) =>
                setTaskProjectId(
                  event.target.value
                )
              }
            >
              <option value="">
                Projectなし
              </option>

              {projects.map(
                (project) => (
                  <option
                    value={project.id}
                    key={project.id}
                  >
                    {project.name}
                  </option>
                )
              )}
            </select>

            <button
              disabled={creatingTask}
            >
              {creatingTask
                ? "作成中..."
                : "Taskを作成"}
            </button>
          </form>

          <div className="list">
            {tasks.length === 0 && (
              <EmptyState text="Taskはまだありません。" />
            )}

            {tasks.map((task) => {
              const project =
                projects.find(
                  (item) =>
                    item.id ===
                    task.project_id
                );

              return (
                <article
                  className="list-item task-item"
                  key={task.id}
                >
                  <div className="item-main">
                    <strong>
                      {task.title}
                    </strong>

                    <span>
                      {project?.name ??
                        "Projectなし"}
                      {" · "}
                      {dateLabel(
                        task.due_at
                      )}
                    </span>
                  </div>

                  <div className="task-actions">
                    <span
                      className={
                        task.risk_level ===
                          "HIGH" ||
                        task.risk_level ===
                          "CRITICAL"
                          ? "risk-badge danger"
                          : "risk-badge"
                      }
                    >
                      {task.risk_level}
                    </span>

                    <select
                      className="status-select"
                      value={task.status}
                      onChange={(event) =>
                        updateTaskStatus(
                          task.id,
                          event.target.value
                        )
                      }
                    >
                      {TASK_STATUSES.map(
                        (status) => (
                          <option
                            value={status}
                            key={status}
                          >
                            {statusLabel(
                              status
                            )}
                          </option>
                        )
                      )}
                    </select>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="panel teams-panel">
        <div className="panel-heading">
          <div>
            <div className="section-kicker">
              TEAMS
            </div>

            <h3>
              Team
            </h3>
          </div>

          <span className="count-pill">
            {teams.length}
          </span>
        </div>

        <div className="team-grid">
          {teams.length === 0 && (
            <EmptyState text="所属Teamはありません。" />
          )}

          {teams.map((team) => (
            <article
              className="team-card"
              key={team.id}
            >
              <strong>
                {team.name}
              </strong>

              <p>
                {team.description ??
                  "説明なし"}
              </p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function MetricCard({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div
      className={
        danger
          ? "metric-card danger"
          : "metric-card"
      }
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <div className="empty-state">
      {text}
    </div>
  );
}
