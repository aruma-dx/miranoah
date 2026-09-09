"use client";

import Link from "next/link";

import {
  useCallback,
  useEffect,
  useState,
} from "react";


type Project = {
  id: string;

  name: string;

  description:
    string | null;

  status: string;

  health: string;

  priority: string;

  progress: number;

  due_at:
    string | null;
};


type Task = {
  id: string;

  project_id:
    string | null;

  title: string;

  description:
    string | null;

  status: string;

  priority: string;

  due_at:
    string | null;

  progress: number;

  risk_level:
    string;
};


type TaskSource = {
  found: boolean;

  source_type:
    string | null;

  slack_message_id:
    string | null;

  slack_channel_id:
    string | null;

  channel_name:
    string | null;

  slack_user_id:
    string | null;

  sender_name:
    string | null;

  text:
    string | null;

  message_ts:
    string | null;

  thread_ts:
    string | null;

  edited_at:
    string | null;

  deleted_at:
    string | null;
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


function taskStatusLabel(
  status: string
) {
  const labels:
    Record<
      string,
      string
    > = {
      CANDIDATE:
        "候補",

      NOT_STARTED:
        "未着手",

      IN_PROGRESS:
        "進行中",

      WAITING_REVIEW:
        "レビュー待ち",

      WAITING_INTERNAL:
        "社内待ち",

      WAITING_EXTERNAL:
        "社外待ち",

      BLOCKED:
        "ブロック",

      ON_HOLD:
        "保留",

      DONE:
        "完了",

      CANCELLED:
        "キャンセル",
    };


  return (
    labels[
      status
    ]
    ?? status
  );
}


function projectStatusLabel(
  status: string
) {
  const labels:
    Record<
      string,
      string
    > = {
      PLANNING:
        "計画中",

      ACTIVE:
        "進行中",

      ON_HOLD:
        "保留",

      BLOCKED:
        "ブロック",

      COMPLETED:
        "完了",

      CANCELLED:
        "キャンセル",

      ARCHIVED:
        "アーカイブ",
    };


  return (
    labels[
      status
    ]
    ?? status
  );
}


function priorityLabel(
  value: string
) {
  const labels:
    Record<
      string,
      string
    > = {
      LOW:
        "低",

      MEDIUM:
        "中",

      HIGH:
        "高",

      CRITICAL:
        "最優先",
    };


  return (
    labels[
      value
    ]
    ?? value
  );
}


function dateLabel(
  value:
    string | null
) {
  if (!value) {
    return (
      "期限なし"
    );
  }


  return new Intl
    .DateTimeFormat(
      "ja-JP",
      {
        year:
          "numeric",

        month:
          "numeric",

        day:
          "numeric",
      }
    )
    .format(
      new Date(
        value
      )
    );
}


function slackTimeLabel(
  value:
    string | null
) {
  if (!value) {
    return "-";
  }


  const seconds =
    Number(
      value
        .split(".")[0]
    );


  if (
    !Number.isFinite(
      seconds
    )
  ) {
    return value;
  }


  return new Intl
    .DateTimeFormat(
      "ja-JP",
      {
        year:
          "numeric",

        month:
          "numeric",

        day:
          "numeric",

        hour:
          "2-digit",

        minute:
          "2-digit",
      }
    )
    .format(
      new Date(
        seconds * 1000
      )
    );
}


type Props = {
  apiBaseUrl:
    string;
};


export function ProjectsListPage({
  apiBaseUrl,
}: Props) {
  const [
    projects,
    setProjects,
  ] =
    useState<
      Project[]
    >([]);


  const [
    loading,
    setLoading,
  ] =
    useState(
      true
    );


  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(null);


  const loadProjects =
    useCallback(
      async () => {
        try {
          setError(
            null
          );


          const response =
            await fetch(
              `${apiBaseUrl}/api/v1/projects`,
              {
                credentials:
                  "include",

                cache:
                  "no-store",
              }
            );


          if (
            !response.ok
          ) {
            throw new Error(
              "Project一覧を取得できませんでした。"
            );
          }


          setProjects(
            await response
              .json()
          );

        } catch (err) {
          setError(
            err
              instanceof
              Error
              ? err.message
              : "エラーが発生しました。"
          );

        } finally {
          setLoading(
            false
          );
        }
      },
      [
        apiBaseUrl,
      ]
    );


  useEffect(
    () => {
      loadProjects();
    },
    [
      loadProjects,
    ]
  );


  return (
    <main>

      <section
        className="hero compact"
      >

        <div
          className="section-kicker"
        >
          PROJECTS
        </div>


        <h2>
          Project一覧
        </h2>


        <p
          className="tagline"
        >
          登録されているProjectを
          新しい順に確認できます。
        </p>

      </section>


      <section
        className="panel"
      >

        <div
          className="panel-heading"
        >

          <div>

            <h3>
              全Project
            </h3>


            <p
              className="panel-description"
            >
              {
                projects.length
              }
              件
            </p>

          </div>


          <Link
            href="/"
            className="secondary-button"
          >
            ← ダッシュボード
          </Link>

        </div>


        {error && (

          <div
            className="error-banner"
          >
            {error}
          </div>

        )}


        {loading ? (

          <div
            className="empty-state"
          >
            読み込み中...
          </div>

        ) : (

          <div
            className="list"
          >

            {projects.map(
              (
                project
              ) => (

                <article
                  className="project-card"
                  key={
                    project.id
                  }
                >

                  <div
                    className="project-card-top"
                  >

                    <div>

                      <strong
                        className="project-title"
                      >
                        {
                          project.name
                        }
                      </strong>


                      <p>
                        {
                          project.description
                          ??
                          "説明なし"
                        }
                      </p>

                    </div>


                    <span
                      className="status-badge"
                    >
                      {projectStatusLabel(
                        project.status
                      )}
                    </span>

                  </div>


                  <div
                    className="project-stats"
                  >

                    <div>

                      <span>
                        優先度
                      </span>

                      <strong>
                        {priorityLabel(
                          project.priority
                        )}
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


                  <div
                    className="progress-track"
                  >

                    <div
                      className="progress-fill"
                      style={{
                        width:
                          `${Math.min(
                            Math.max(
                              project.progress,
                              0
                            ),
                            100
                          )}%`,
                      }}
                    />

                  </div>

                </article>

              )
            )}

          </div>

        )}

      </section>

    </main>
  );
}


export function TasksListPage({
  apiBaseUrl,
}: Props) {
  const [
    tasks,
    setTasks,
  ] =
    useState<
      Task[]
    >([]);


  const [
    projects,
    setProjects,
  ] =
    useState<
      Project[]
    >([]);


  const [
    sources,
    setSources,
  ] =
    useState<
      Record<
        string,
        TaskSource
      >
    >({});


  const [
    sourceOpenId,
    setSourceOpenId,
  ] =
    useState<
      string | null
    >(null);


  const [
    sourceLoadingId,
    setSourceLoadingId,
  ] =
    useState<
      string | null
    >(null);


  const [
    loading,
    setLoading,
  ] =
    useState(
      true
    );


  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(null);


  const loadData =
    useCallback(
      async () => {
        try {
          setError(
            null
          );


          const [
            tasksResponse,
            projectsResponse,
          ] =
            await Promise.all([
              fetch(
                `${apiBaseUrl}/api/v1/tasks?limit=500`,
                {
                  credentials:
                    "include",

                  cache:
                    "no-store",
                }
              ),

              fetch(
                `${apiBaseUrl}/api/v1/projects`,
                {
                  credentials:
                    "include",

                  cache:
                    "no-store",
                }
              ),
            ]);


          if (
            !tasksResponse.ok
            ||
            !projectsResponse.ok
          ) {
            throw new Error(
              "Task一覧を取得できませんでした。"
            );
          }


          setTasks(
            await tasksResponse
              .json()
          );


          setProjects(
            await projectsResponse
              .json()
          );

        } catch (err) {
          setError(
            err
              instanceof
              Error
              ? err.message
              : "エラーが発生しました。"
          );

        } finally {
          setLoading(
            false
          );
        }
      },
      [
        apiBaseUrl,
      ]
    );


  useEffect(
    () => {
      loadData();
    },
    [
      loadData,
    ]
  );


  async function toggleSource(
    taskId: string
  ) {
    if (
      sourceOpenId
      === taskId
    ) {
      setSourceOpenId(
        null
      );

      return;
    }


    if (
      !sources[
        taskId
      ]
    ) {
      try {
        setSourceLoadingId(
          taskId
        );

        setError(
          null
        );


        const response =
          await fetch(
            `${apiBaseUrl}/api/v1/tasks/${taskId}/source`,
            {
              credentials:
                "include",

              cache:
                "no-store",
            }
          );


        if (
          !response.ok
        ) {
          throw new Error(
            "Taskの出典取得に失敗しました。"
          );
        }


        const source:
          TaskSource =
          await response
            .json();


        setSources(
          (
            current
          ) => ({
            ...current,

            [taskId]:
              source,
          })
        );

      } catch (err) {
        setError(
          err
            instanceof
            Error
            ? err.message
            : "Taskの出典取得に失敗しました。"
        );

        return;

      } finally {
        setSourceLoadingId(
          null
        );
      }
    }


    setSourceOpenId(
      taskId
    );
  }


  async function updateStatus(
    taskId: string,

    status: string
  ) {
    const response =
      await fetch(
        `${apiBaseUrl}/api/v1/tasks/${taskId}`,
        {
          method:
            "PATCH",

          credentials:
            "include",

          headers: {
            "Content-Type":
              "application/json",
          },

          body:
            JSON.stringify({
              status,
            }),
        }
      );


    if (
      !response.ok
    ) {
      setError(
        "Taskの更新に失敗しました。"
      );

      return;
    }


    await loadData();
  }


  return (
    <main>

      <section
        className="hero compact"
      >

        <div
          className="section-kicker"
        >
          TASKS
        </div>


        <h2>
          Task一覧
        </h2>


        <p
          className="tagline"
        >
          登録されているTaskを
          期限が近い順に確認できます。
        </p>

      </section>


      <section
        className="panel"
      >

        <div
          className="panel-heading"
        >

          <div>

            <h3>
              全Task
            </h3>


            <p
              className="panel-description"
            >
              {
                tasks.length
              }
              件
            </p>

          </div>


          <Link
            href="/"
            className="secondary-button"
          >
            ← ダッシュボード
          </Link>

        </div>


        {error && (

          <div
            className="error-banner"
          >
            {error}
          </div>

        )}


        <div
          className="task-table-header"
        >
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


        {loading ? (

          <div
            className="empty-state"
          >
            読み込み中...
          </div>

        ) : (

          <div
            className="list"
          >

            {tasks.map(
              (
                task
              ) => {

                const project =
                  projects.find(
                    (
                      item
                    ) =>
                      item.id
                      ===
                      task.project_id
                  );


                const source =
                  sources[
                    task.id
                  ];


                const sourceIsOpen =
                  sourceOpenId
                  ===
                  task.id;


                return (

                  <article
                    key={
                      task.id
                    }
                  >

                    <div
                      className="task-row"
                    >

                      <div
                        className="task-main"
                      >

                        <strong>
                          {
                            task.title
                          }
                        </strong>


                        <span>
                          {project?.name
                            ??
                            "Projectなし"}

                          {" ・ "}

                          {dateLabel(
                            task.due_at
                          )}
                        </span>


                        <button
                          className="secondary-button"
                          style={{
                            marginTop:
                              "8px",

                            width:
                              "fit-content",
                          }}
                          disabled={
                            sourceLoadingId
                            ===
                            task.id
                          }
                          onClick={() =>
                            toggleSource(
                              task.id
                            )
                          }
                        >
                          {sourceLoadingId
                            ===
                            task.id
                            ? "出典取得中..."
                            : sourceIsOpen
                            ? "出典を閉じる"
                            : "出典を見る"}
                        </button>

                      </div>


                      <span
                        className="priority-badge"
                      >
                        {priorityLabel(
                          task.priority
                        )}
                      </span>


                      <span
                        className={
                          task.risk_level
                          ===
                          "HIGH"
                          ||
                          task.risk_level
                          ===
                          "CRITICAL"
                            ? "risk-badge danger"
                            : "risk-badge"
                        }
                      >
                        {priorityLabel(
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
                          updateStatus(
                            task.id,
                            event
                              .target
                              .value
                          )
                        }
                      >

                        {TASK_STATUSES.map(
                          (
                            status
                          ) => (

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

                    </div>


                    {sourceIsOpen && (

                      <div
                        style={{
                          margin:
                            "8px 0 18px",

                          padding:
                            "18px",

                          border:
                            "1px solid currentColor",

                          borderRadius:
                            "12px",
                        }}
                      >

                        {!source ? (

                          <p>
                            出典を読み込んでいます。
                          </p>

                        ) : !source.found ? (

                          <>

                            <div
                              className="section-kicker"
                            >
                              SOURCE
                            </div>


                            <p>
                              このTaskにはSlack出典がありません。
                              手動作成Taskなどの可能性があります。
                            </p>

                          </>

                        ) : (

                          <>

                            <div
                              className="section-kicker"
                            >
                              SOURCE / SLACK
                            </div>


                            <p>

                              <strong>
                                {source.channel_name
                                  ? `#${source.channel_name}`
                                  : source.slack_channel_id
                                  ??
                                  "チャンネル不明"}
                              </strong>


                              {" ・ "}


                              {source.sender_name
                                ??
                                source.slack_user_id
                                ??
                                "投稿者不明"}


                              {" ・ "}


                              {slackTimeLabel(
                                source.message_ts
                              )}

                            </p>


                            <p
                              style={{
                                whiteSpace:
                                  "pre-wrap",

                                marginTop:
                                  "12px",
                              }}
                            >
                              {source.text
                                ??
                                "本文なし"}
                            </p>


                            {source.edited_at && (

                              <p
                                className="panel-description"
                              >
                                ※ 元のSlackメッセージは編集されています。
                              </p>

                            )}


                            {source.deleted_at && (

                              <p
                                className="panel-description"
                              >
                                ※ 元のSlackメッセージは削除されています。
                              </p>

                            )}

                          </>

                        )}

                      </div>

                    )}

                  </article>

                );
              }
            )}

          </div>

        )}

      </section>

    </main>
  );
}
