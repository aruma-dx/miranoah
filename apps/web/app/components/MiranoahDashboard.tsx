"use client";

import Link from "next/link";

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

type ModalType =
  | "project"
  | "task"
  | null;

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

const PRIORITIES = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

function taskStatusLabel(
  status: string
) {
  const labels: Record<
    string,
    string
  > = {
    CANDIDATE: "候補",
    NOT_STARTED: "未着手",
    IN_PROGRESS: "進行中",
    WAITING_REVIEW: "レビュー待ち",
    WAITING_INTERNAL: "社内待ち",
    WAITING_EXTERNAL: "社外待ち",
    BLOCKED: "ブロック",
    ON_HOLD: "保留",
    DONE: "完了",
    CANCELLED: "キャンセル",
  };

  return labels[status] ?? status;
}

function projectStatusLabel(
  status: string
) {
  const labels: Record<
    string,
    string
  > = {
    PLANNING: "計画中",
    ACTIVE: "進行中",
    ON_HOLD: "保留",
    BLOCKED: "ブロック",
    COMPLETED: "完了",
    CANCELLED: "キャンセル",
    ARCHIVED: "アーカイブ",
  };

  return labels[status] ?? status;
}

function priorityLabel(
  priority: string
) {
  const labels: Record<
    string,
    string
  > = {
    LOW: "低",
    MEDIUM: "中",
    HIGH: "高",
    CRITICAL: "最優先",
  };

  return labels[priority] ?? priority;
}

function riskLabel(
  risk: string
) {
  const labels: Record<
    string,
    string
  > = {
    LOW: "低",
    MEDIUM: "中",
    HIGH: "高",
    CRITICAL: "重大",
  };

  return labels[risk] ?? risk;
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
      year: "numeric",
      month: "numeric",
      day: "numeric",
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

  const [
    reviewCandidates,
    setReviewCandidates,
  ] = useState<Task[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [success, setSuccess] =
    useState<string | null>(null);

  const [modal, setModal] =
    useState<ModalType>(null);

  const [
    projectName,
    setProjectName,
  ] = useState("");

  const [
    projectDescription,
    setProjectDescription,
  ] = useState("");

  const [
    projectPriority,
    setProjectPriority,
  ] = useState("MEDIUM");

  const [
    projectDueAt,
    setProjectDueAt,
  ] = useState("");

  const [
    taskTitle,
    setTaskTitle,
  ] = useState("");

  const [
    taskDescription,
    setTaskDescription,
  ] = useState("");

  const [
    taskProjectId,
    setTaskProjectId,
  ] = useState("");

  const [
    taskPriority,
    setTaskPriority,
  ] = useState("MEDIUM");

  const [
    taskDueAt,
    setTaskDueAt,
  ] = useState("");

  const [
    creatingProject,
    setCreatingProject,
  ] = useState(false);

  const [
    creatingTask,
    setCreatingTask,
  ] = useState(false);

  const apiFetch =
    useCallback(
      async (
        path: string,
        options?: RequestInit
      ) => {
        return fetch(
          `${apiBaseUrl}${path}`,
          {
            ...options,
            credentials:
              "include",
            cache:
              "no-store",
            headers: {
              "Content-Type":
                "application/json",
              ...(options?.headers ??
                {}),
            },
          }
        );
      },
      [apiBaseUrl]
    );

  const loadData =
    useCallback(
      async () => {
        setError(null);

        try {
          const meResponse =
            await apiFetch(
              "/api/v1/auth/me"
            );

          if (!meResponse.ok) {
            setUser(null);
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
            reviewsResponse,
          ] =
            await Promise.all([
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
              apiFetch(
                "/api/v1/ai-reviews"
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

          if (
            reviewsResponse.ok
          ) {
            setReviewCandidates(
              await reviewsResponse.json()
            );
          } else {
            setReviewCandidates([]);
          }
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

  const recentProjects =
    projects.slice(0, 5);

  const upcomingTasks =
    tasks
      .filter(
        (task) =>
          task.status !== "DONE" &&
          task.status !==
            "CANCELLED" &&
          task.status !==
            "CANDIDATE"
      )
      .slice(0, 5);

  function openProjectModal() {
    setError(null);
    setSuccess(null);

    setProjectName("");
    setProjectDescription("");
    setProjectPriority(
      "MEDIUM"
    );
    setProjectDueAt("");

    setModal("project");
  }

  function openTaskModal(
    projectId = ""
  ) {
    setError(null);
    setSuccess(null);

    setTaskTitle("");
    setTaskDescription("");
    setTaskProjectId(
      projectId
    );
    setTaskPriority(
      "MEDIUM"
    );
    setTaskDueAt("");

    setModal("task");
  }

  function closeModal() {
    if (
      creatingProject ||
      creatingTask
    ) {
      return;
    }

    setModal(null);
  }

  function showSuccess(
    message: string
  ) {
    setSuccess(message);

    window.setTimeout(
      () => {
        setSuccess(null);
      },
      4000
    );
  }

  async function createProject(
    event: FormEvent
  ) {
    event.preventDefault();

    if (
      !projectName.trim()
    ) {
      setError(
        "Project名を入力してください。"
      );
      return;
    }

    setCreatingProject(
      true
    );
    setError(null);

    try {
      const response =
        await apiFetch(
          "/api/v1/projects",
          {
            method: "POST",
            body:
              JSON.stringify({
                name:
                  projectName.trim(),
                description:
                  projectDescription.trim() ||
                  null,
                priority:
                  projectPriority,
                due_at:
                  projectDueAt
                    ? new Date(
                        `${projectDueAt}T23:59:59`
                      ).toISOString()
                    : null,
              }),
          }
        );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => null
            );

        throw new Error(
          body?.detail ??
            "Projectの作成に失敗しました。"
        );
      }

      setModal(null);

      showSuccess(
        `「${projectName.trim()}」を作成しました。`
      );

      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Projectの作成に失敗しました。"
      );
    } finally {
      setCreatingProject(
        false
      );
    }
  }

  async function createTask(
    event: FormEvent
  ) {
    event.preventDefault();

    if (
      !taskTitle.trim()
    ) {
      setError(
        "Task名を入力してください。"
      );
      return;
    }

    setCreatingTask(
      true
    );
    setError(null);

    try {
      const response =
        await apiFetch(
          "/api/v1/tasks",
          {
            method: "POST",
            body:
              JSON.stringify({
                title:
                  taskTitle.trim(),
                description:
                  taskDescription.trim() ||
                  null,
                project_id:
                  taskProjectId ||
                  null,
                priority:
                  taskPriority,
                due_at:
                  taskDueAt
                    ? new Date(
                        `${taskDueAt}T23:59:59`
                      ).toISOString()
                    : null,
              }),
          }
        );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => null
            );

        throw new Error(
          body?.detail ??
            "Taskの作成に失敗しました。"
        );
      }

      setModal(null);

      showSuccess(
        `「${taskTitle.trim()}」を作成しました。`
      );

      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Taskの作成に失敗しました。"
      );
    } finally {
      setCreatingTask(
        false
      );
    }
  }

  async function updateTaskStatus(
    taskId: string,
    status: string
  ) {
    setError(null);

    const response =
      await apiFetch(
        `/api/v1/tasks/${taskId}`,
        {
          method: "PATCH",
          body:
            JSON.stringify({
              status,
            }),
        }
      );

    if (!response.ok) {
      const body =
        await response
          .json()
          .catch(
            () => null
          );

      setError(
        body?.detail ??
          "Taskの更新に失敗しました。"
      );

      return;
    }

    showSuccess(
      "Taskの状態を更新しました。"
    );

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

      {success && (
        <div className="success-banner">
          <span>
            ✓
          </span>
          {success}
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
            Project・Task・期限・リスクの
            直近状況を確認できます。
          </p>
        </div>

        <div className="welcome-actions">
          <Link
            href="/reviews"
            className="secondary-button"
          >
            AIレビュー
            {reviewCandidates.length >
            0
              ? ` ${reviewCandidates.length}件`
              : ""}
          </Link>

          <button
            className="secondary-button"
            onClick={
              loadData
            }
          >
            ↻ 更新
          </button>

          <button
            className="primary-button"
            onClick={() =>
              openTaskModal()
            }
          >
            ＋ Taskを作成
          </button>

          <button
            className="primary-button"
            onClick={
              openProjectModal
            }
          >
            ＋ Projectを作成
          </button>
        </div>
      </section>

      <section className="metrics-grid">
        <MetricCard
          label="進行中Project"
          value={
            summary?.active_projects ??
            0
          }
        />

        <MetricCard
          label="未完了Task"
          value={
            summary?.open_tasks ??
            0
          }
        />

        <MetricCard
          label="AIレビュー"
          value={
            reviewCandidates.length
          }
          danger={
            reviewCandidates.length >
            0
          }
        />

        <MetricCard
          label="期限超過"
          value={
            summary?.overdue ??
            0
          }
          danger={
            (summary?.overdue ??
              0) > 0
          }
        />

        <MetricCard
          label="高リスク"
          value={
            summary?.high_risk ??
            0
          }
          danger={
            (summary?.high_risk ??
              0) > 0
          }
        />
      </section>

      {reviewCandidates.length >
        0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">
                ACTION REQUIRED
              </div>

              <h3>
                AIレビューが必要です
              </h3>

              <p className="panel-description">
                AIが自動登録を保留したTask候補が
                {reviewCandidates.length}
                件あります。
              </p>
            </div>

            <Link
              href="/reviews"
              className="primary-button"
            >
              AIレビューを確認
            </Link>
          </div>
        </section>
      )}

      <section className="workspace-grid">
        <div className="panel">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">
                RECENT PROJECTS
              </div>

              <h3>
                最新のProject
              </h3>

              <p className="panel-description">
                最近作成されたProjectを
                最大5件表示しています。
              </p>
            </div>

            <div className="welcome-actions">
              <Link
                href="/projects"
                className="secondary-button"
              >
                一覧を見る
              </Link>

              <button
                className="panel-create-button"
                onClick={
                  openProjectModal
                }
              >
                ＋ 作成
              </button>
            </div>
          </div>

          <div className="list">
            {recentProjects.length ===
              0 && (
              <div className="empty-state enhanced">
                <strong>
                  Projectがありません
                </strong>

                <p>
                  まず最初のProjectを作成しましょう。
                </p>

                <button
                  className="primary-button"
                  onClick={
                    openProjectModal
                  }
                >
                  ＋ Projectを作成
                </button>
              </div>
            )}

            {recentProjects.map(
              (project) => {
                const projectTaskCount =
                  tasks.filter(
                    (task) =>
                      task.project_id ===
                        project.id &&
                      task.status !==
                        "CANDIDATE"
                  ).length;

                return (
                  <article
                    className="project-card"
                    key={
                      project.id
                    }
                  >
                    <div className="project-card-top">
                      <div>
                        <strong className="project-title">
                          {
                            project.name
                          }
                        </strong>

                        <p>
                          {project.description ??
                            "説明なし"}
                        </p>
                      </div>

                      <span className="status-badge">
                        {projectStatusLabel(
                          project.status
                        )}
                      </span>
                    </div>

                    <div className="project-stats">
                      <div>
                        <span>
                          Task
                        </span>

                        <strong>
                          {
                            projectTaskCount
                          }
                          件
                        </strong>
                      </div>

                      <div>
                        <span>
                          進捗
                        </span>

                        <strong>
                          {
                            project.progress
                          }
                          %
                        </strong>
                      </div>

                      <div>
                        <span>
                          期限
                        </span>

                        <strong>
                          {dateLabel(
                            project.due_at
                          )}
                        </strong>
                      </div>
                    </div>

                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min(
                            Math.max(
                              project.progress,
                              0
                            ),
                            100
                          )}%`,
                        }}
                      />
                    </div>

                    <div className="project-actions">
                      <button
                        onClick={() =>
                          openTaskModal(
                            project.id
                          )
                        }
                      >
                        ＋ Taskを追加
                      </button>
                    </div>
                  </article>
                );
              }
            )}
          </div>
        </div>

        <div className="panel task-panel">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">
                UPCOMING TASKS
              </div>

              <h3>
                直近のTask
              </h3>

              <p className="panel-description">
                期限が近い未完了Taskを
                最大5件表示しています。
              </p>
            </div>

            <div className="welcome-actions">
              <Link
                href="/tasks"
                className="secondary-button"
              >
                一覧を見る
              </Link>

              <button
                className="panel-create-button"
                onClick={() =>
                  openTaskModal()
                }
              >
                ＋ 作成
              </button>
            </div>
          </div>

          <div className="task-table-header">
            <span>
              Task
            </span>
            <span>
              優先度
            </span>
            <span>
              リスク
            </span>
            <span>
              状態
            </span>
          </div>

          <div className="list">
            {upcomingTasks.length ===
              0 && (
              <div className="empty-state enhanced">
                <strong>
                  未完了Taskがありません
                </strong>

                <p>
                  新しいTaskを登録してみましょう。
                </p>

                <button
                  className="primary-button"
                  onClick={() =>
                    openTaskModal()
                  }
                >
                  ＋ Taskを作成
                </button>
              </div>
            )}

            {upcomingTasks.map(
              (task) => {
                const project =
                  projects.find(
                    (item) =>
                      item.id ===
                      task.project_id
                  );

                return (
                  <article
                    className="task-row"
                    key={
                      task.id
                    }
                  >
                    <div className="task-main">
                      <strong>
                        {
                          task.title
                        }
                      </strong>

                      <span>
                        {project?.name ??
                          "Projectなし"}
                        {" ・ "}
                        {dateLabel(
                          task.due_at
                        )}
                      </span>
                    </div>

                    <span className="priority-badge">
                      {priorityLabel(
                        task.priority
                      )}
                    </span>

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
                      {riskLabel(
                        task.risk_level
                      )}
                    </span>

                    <select
                      className="status-select"
                      value={
                        task.status
                      }
                      onChange={(
                        event
                      ) =>
                        updateTaskStatus(
                          task.id,
                          event
                            .target
                            .value
                        )
                      }
                    >
                      {TASK_STATUSES.map(
                        (status) => (
                          <option
                            value={
                              status
                            }
                            key={
                              status
                            }
                          >
                            {taskStatusLabel(
                              status
                            )}
                          </option>
                        )
                      )}
                    </select>
                  </article>
                );
              }
            )}
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

            <p className="panel-description">
              あなたが所属・管理しているTeamです。
            </p>
          </div>

          <span className="count-pill">
            {
              teams.length
            }
          </span>
        </div>

        <div className="team-grid">
          {teams.length ===
            0 && (
            <div className="empty-state">
              所属Teamはありません。
            </div>
          )}

          {teams.map(
            (team) => (
              <article
                className="team-card"
                key={
                  team.id
                }
              >
                <strong>
                  {
                    team.name
                  }
                </strong>

                <p>
                  {team.description ??
                    "説明なし"}
                </p>
              </article>
            )
          )}
        </div>
      </section>

      {modal ===
        "project" && (
        <div
          className="modal-backdrop"
          onMouseDown={(
            event
          ) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeModal();
            }
          }}
        >
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <div className="section-kicker">
                  NEW PROJECT
                </div>

                <h2>
                  Projectを作成
                </h2>

                <p>
                  案件・施策・開発など、
                  複数のTaskをまとめる単位です。
                </p>
              </div>

              <button
                className="modal-close"
                onClick={
                  closeModal
                }
                type="button"
              >
                ×
              </button>
            </div>

            <form
              className="modal-form"
              onSubmit={
                createProject
              }
            >
              <label className="form-field">
                <span>
                  Project名
                  <em>
                    必須
                  </em>
                </span>

                <input
                  autoFocus
                  value={
                    projectName
                  }
                  onChange={(
                    event
                  ) =>
                    setProjectName(
                      event
                        .target
                        .value
                    )
                  }
                  placeholder="例：神奈川県教育委員会案件"
                />
              </label>

              <label className="form-field">
                <span>
                  概要
                  <small>
                    任意
                  </small>
                </span>

                <textarea
                  value={
                    projectDescription
                  }
                  onChange={(
                    event
                  ) =>
                    setProjectDescription(
                      event
                        .target
                        .value
                    )
                  }
                  placeholder="このProjectで何を行うか入力"
                />
              </label>

              <div className="form-grid-two">
                <label className="form-field">
                  <span>
                    優先度
                  </span>

                  <select
                    value={
                      projectPriority
                    }
                    onChange={(
                      event
                    ) =>
                      setProjectPriority(
                        event
                          .target
                          .value
                      )
                    }
                  >
                    {PRIORITIES.map(
                      (
                        priority
                      ) => (
                        <option
                          value={
                            priority
                          }
                          key={
                            priority
                          }
                        >
                          {priorityLabel(
                            priority
                          )}
                        </option>
                      )
                    )}
                  </select>
                </label>

                <label className="form-field">
                  <span>
                    期限
                    <small>
                      任意
                    </small>
                  </span>

                  <input
                    type="date"
                    value={
                      projectDueAt
                    }
                    onChange={(
                      event
                    ) =>
                      setProjectDueAt(
                        event
                          .target
                          .value
                      )
                    }
                  />
                </label>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={
                    closeModal
                  }
                >
                  キャンセル
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={
                    creatingProject
                  }
                >
                  {creatingProject
                    ? "作成中..."
                    : "Projectを作成"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modal ===
        "task" && (
        <div
          className="modal-backdrop"
          onMouseDown={(
            event
          ) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeModal();
            }
          }}
        >
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <div className="section-kicker">
                  NEW TASK
                </div>

                <h2>
                  Taskを作成
                </h2>

                <p>
                  実際に対応する具体的な仕事を登録します。
                </p>
              </div>

              <button
                className="modal-close"
                onClick={
                  closeModal
                }
                type="button"
              >
                ×
              </button>
            </div>

            <form
              className="modal-form"
              onSubmit={
                createTask
              }
            >
              <label className="form-field">
                <span>
                  所属Project
                  <small>
                    任意
                  </small>
                </span>

                <select
                  value={
                    taskProjectId
                  }
                  onChange={(
                    event
                  ) =>
                    setTaskProjectId(
                      event
                        .target
                        .value
                    )
                  }
                >
                  <option value="">
                    Projectなし
                  </option>

                  {projects.map(
                    (
                      project
                    ) => (
                      <option
                        value={
                          project.id
                        }
                        key={
                          project.id
                        }
                      >
                        {
                          project.name
                        }
                      </option>
                    )
                  )}
                </select>
              </label>

              <label className="form-field">
                <span>
                  Task名
                  <em>
                    必須
                  </em>
                </span>

                <input
                  autoFocus
                  value={
                    taskTitle
                  }
                  onChange={(
                    event
                  ) =>
                    setTaskTitle(
                      event
                        .target
                        .value
                    )
                  }
                  placeholder="例：企画書の初稿を作成"
                />
              </label>

              <label className="form-field">
                <span>
                  詳細
                  <small>
                    任意
                  </small>
                </span>

                <textarea
                  value={
                    taskDescription
                  }
                  onChange={(
                    event
                  ) =>
                    setTaskDescription(
                      event
                        .target
                        .value
                    )
                  }
                  placeholder="対応内容や完了条件などを入力"
                />
              </label>

              <div className="form-grid-two">
                <label className="form-field">
                  <span>
                    優先度
                  </span>

                  <select
                    value={
                      taskPriority
                    }
                    onChange={(
                      event
                    ) =>
                      setTaskPriority(
                        event
                          .target
                          .value
                      )
                    }
                  >
                    {PRIORITIES.map(
                      (
                        priority
                      ) => (
                        <option
                          value={
                            priority
                          }
                          key={
                            priority
                          }
                        >
                          {priorityLabel(
                            priority
                          )}
                        </option>
                      )
                    )}
                  </select>
                </label>

                <label className="form-field">
                  <span>
                    期限
                    <small>
                      任意
                    </small>
                  </span>

                  <input
                    type="date"
                    value={
                      taskDueAt
                    }
                    onChange={(
                      event
                    ) =>
                      setTaskDueAt(
                        event
                          .target
                          .value
                      )
                    }
                  />
                </label>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={
                    closeModal
                  }
                >
                  キャンセル
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={
                    creatingTask
                  }
                >
                  {creatingTask
                    ? "作成中..."
                    : "Taskを作成"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
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
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}
