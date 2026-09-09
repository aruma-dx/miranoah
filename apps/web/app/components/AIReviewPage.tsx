"use client";

import Link from "next/link";

import {
  useCallback,
  useEffect,
  useState,
} from "react";


type Task = {
  id: string;

  project_id: string | null;

  title: string;

  description: string | null;

  status: string;

  priority: string;

  requester_id: string | null;

  owner_id: string | null;

  due_at: string | null;

  deadline_type: string | null;

  deadline_confidence:
    number | null;

  ai_generated: boolean;

  ai_confidence:
    number | null;
};


type Project = {
  id: string;
  name: string;
};


type Draft = {
  title: string;

  description: string;

  projectId: string;

  priority: string;

  dueAt: string;
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


type Props = {
  apiBaseUrl: string;
};


const PRIORITIES = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];


function priorityLabel(
  value: string
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

  return (
    labels[value]
    ?? value
  );
}


function deadlineTypeLabel(
  value: string | null
) {
  if (!value) {
    return "期限なし";
  }

  const labels: Record<
    string,
    string
  > = {
    EXPLICIT:
      "本文に明記",

    RELATIVE:
      "相対期限",

    CALENDAR_BASED:
      "カレンダー基準",

    AI_INFERRED:
      "AI推定",

    MANUAL:
      "手動確認",
  };

  return (
    labels[value]
    ?? value
  );
}


function confidenceLabel(
  value: number | null
) {
  if (value === null) {
    return "-";
  }

  return `${Math.round(
    value * 100
  )}%`;
}


function toDateInput(
  value: string | null
) {
  if (!value) {
    return "";
  }

  const date =
    new Date(value);

  const year =
    date.getFullYear();

  const month =
    String(
      date.getMonth() + 1
    ).padStart(
      2,
      "0"
    );

  const day =
    String(
      date.getDate()
    ).padStart(
      2,
      "0"
    );

  return (
    `${year}-${month}-${day}`
  );
}


function createDraft(
  task: Task
): Draft {
  return {
    title:
      task.title,

    description:
      task.description ?? "",

    projectId:
      task.project_id ?? "",

    priority:
      task.priority,

    dueAt:
      toDateInput(
        task.due_at
      ),
  };
}


function slackTimeLabel(
  value: string | null
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


export default function AIReviewPage({
  apiBaseUrl,
}: Props) {
  const [
    candidates,
    setCandidates,
  ] = useState<Task[]>([]);

  const [
    projects,
    setProjects,
  ] = useState<Project[]>([]);

  const [
    drafts,
    setDrafts,
  ] = useState<
    Record<
      string,
      Draft
    >
  >({});

  const [
    sources,
    setSources,
  ] = useState<
    Record<
      string,
      TaskSource
    >
  >({});

  const [
    sourceOpenId,
    setSourceOpenId,
  ] = useState<
    string | null
  >(null);

  const [
    sourceLoadingId,
    setSourceLoadingId,
  ] = useState<
    string | null
  >(null);

  const [
    editingId,
    setEditingId,
  ] = useState<
    string | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(
    true
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    success,
    setSuccess,
  ] = useState<
    string | null
  >(null);

  const [
    processingId,
    setProcessingId,
  ] = useState<
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
            reviewsResponse,
            projectsResponse,
          ] =
            await Promise.all([
              fetch(
                `${apiBaseUrl}/api/v1/ai-reviews`,
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
            !reviewsResponse.ok
          ) {
            throw new Error(
              "AIレビュー候補を取得できませんでした。"
            );
          }


          if (
            !projectsResponse.ok
          ) {
            throw new Error(
              "Project情報を取得できませんでした。"
            );
          }


          const reviewData:
            Task[] =
            await reviewsResponse
              .json();


          const projectData:
            Project[] =
            await projectsResponse
              .json();


          setCandidates(
            reviewData
          );


          setProjects(
            projectData
          );


          const nextDrafts:
            Record<
              string,
              Draft
            > = {};


          reviewData.forEach(
            (
              task
            ) => {
              nextDrafts[
                task.id
              ] =
                createDraft(
                  task
                );
            }
          );


          setDrafts(
            nextDrafts
          );

        } catch (err) {
          setError(
            err instanceof Error
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


        if (!response.ok) {
          throw new Error(
            "Slack出典の取得に失敗しました。"
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
          err instanceof Error
            ? err.message
            : "Slack出典の取得に失敗しました。"
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


  function startEditing(
    task: Task
  ) {
    setDrafts(
      (
        current
      ) => ({
        ...current,

        [task.id]:
          createDraft(
            task
          ),
      })
    );

    setEditingId(
      task.id
    );

    setError(
      null
    );

    setSuccess(
      null
    );
  }


  function cancelEditing(
    task: Task
  ) {
    setDrafts(
      (
        current
      ) => ({
        ...current,

        [task.id]:
          createDraft(
            task
          ),
      })
    );

    setEditingId(
      null
    );
  }


  function updateDraft(
    taskId: string,

    key:
      keyof Draft,

    value: string
  ) {
    setDrafts(
      (
        current
      ) => ({
        ...current,

        [taskId]: {
          ...current[
            taskId
          ],

          [key]:
            value,
        },
      })
    );
  }


  async function approveTask(
    task: Task,

    useDraft:
      boolean
  ) {
    try {
      setProcessingId(
        task.id
      );

      setError(
        null
      );

      setSuccess(
        null
      );


      const options:
        RequestInit = {
          method:
            "POST",

          credentials:
            "include",
        };


      if (
        useDraft
      ) {
        const draft =
          drafts[
            task.id
          ];


        if (
          !draft
          ||
          !draft
            .title
            .trim()
        ) {
          throw new Error(
            "Task名を入力してください。"
          );
        }


        options.headers = {
          "Content-Type":
            "application/json",
        };


        options.body =
          JSON.stringify({
            title:
              draft
                .title
                .trim(),

            description:
              draft
                .description
                .trim()
                || null,

            project_id:
              draft
                .projectId
                || null,

            priority:
              draft
                .priority,

            due_at:
              draft
                .dueAt
                ? new Date(
                    `${draft.dueAt}T23:59:59`
                  )
                    .toISOString()
                : null,
          });
      }


      const response =
        await fetch(
          `${apiBaseUrl}/api/v1/ai-reviews/${task.id}/approve`,
          options
        );


      if (
        !response.ok
      ) {
        const body =
          await response
            .json()
            .catch(
              () => null
            );


        throw new Error(
          body?.detail
          ??
          "Taskの承認に失敗しました。"
        );
      }


      setEditingId(
        null
      );

      setSourceOpenId(
        null
      );


      setSuccess(
        useDraft
          ? "内容を修正してTaskを承認しました。"
          : "Taskを承認しました。"
      );


      await loadData();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "エラーが発生しました。"
      );

    } finally {
      setProcessingId(
        null
      );
    }
  }


  async function rejectTask(
    taskId: string
  ) {
    try {
      setProcessingId(
        taskId
      );

      setError(
        null
      );

      setSuccess(
        null
      );


      const response =
        await fetch(
          `${apiBaseUrl}/api/v1/ai-reviews/${taskId}/reject`,
          {
            method:
              "POST",

            credentials:
              "include",
          }
        );


      if (
        !response.ok
      ) {
        const body =
          await response
            .json()
            .catch(
              () => null
            );


        throw new Error(
          body?.detail
          ??
          "Task候補の却下に失敗しました。"
        );
      }


      if (
        editingId
        === taskId
      ) {
        setEditingId(
          null
        );
      }


      if (
        sourceOpenId
        === taskId
      ) {
        setSourceOpenId(
          null
        );
      }


      setSuccess(
        "Task候補を却下しました。"
      );


      await loadData();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "エラーが発生しました。"
      );

    } finally {
      setProcessingId(
        null
      );
    }
  }


  return (
    <main>

      {error && (
        <div
          className="error-banner"
        >
          {error}
        </div>
      )}


      {success && (
        <div
          className="success-banner"
        >
          {success}
        </div>
      )}


      <section
        className="hero compact"
      >
        <div
          className="section-kicker"
        >
          AI REVIEW QUEUE
        </div>


        <h2>
          AIレビュー
        </h2>


        <p
          className="tagline"
        >
          AIが自動登録を保留したTaskを確認し、
          元のSlack発言を確認しながら承認できます。
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
              確認待ち
            </h3>


            <p
              className="panel-description"
            >
              {candidates.length}
              件の候補があります
            </p>

          </div>


          <Link
            href="/"
            className="secondary-button"
          >
            ← ダッシュボード
          </Link>

        </div>


        {loading ? (

          <div
            className="empty-state"
          >
            読み込み中...
          </div>

        ) : candidates.length
          === 0 ? (

          <div
            className="empty-state enhanced"
          >

            <strong>
              確認待ちはありません
            </strong>


            <p>
              AIが判断に迷ったTaskが
              ここに表示されます。
            </p>

          </div>

        ) : (

          <div
            className="list"
          >

            {candidates.map(
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


                const isEditing =
                  editingId
                  ===
                  task.id;


                const draft =
                  drafts[
                    task.id
                  ];


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
                    className="project-card"
                    key={
                      task.id
                    }
                  >

                    <div
                      className="project-card-top"
                    >

                      <div>

                        <strong
                          className="project-title"
                        >
                          {task.title}
                        </strong>


                        <p>
                          {task.description
                            ??
                            "説明なし"}
                        </p>

                      </div>


                      <span
                        className="status-badge"
                      >
                        AI候補
                      </span>

                    </div>


                    <div
                      className="project-stats"
                    >

                      <div>
                        <span>
                          AI確信度
                        </span>

                        <strong>
                          {confidenceLabel(
                            task.ai_confidence
                          )}
                        </strong>
                      </div>


                      <div>
                        <span>
                          期限判定
                        </span>

                        <strong>
                          {deadlineTypeLabel(
                            task.deadline_type
                          )}
                        </strong>
                      </div>


                      <div>
                        <span>
                          期限確信度
                        </span>

                        <strong>
                          {confidenceLabel(
                            task.deadline_confidence
                          )}
                        </strong>
                      </div>

                    </div>


                    <div
                      className="project-stats"
                    >

                      <div>
                        <span>
                          Project
                        </span>

                        <strong>
                          {project?.name
                            ??
                            "Projectなし"}
                        </strong>
                      </div>


                      <div>
                        <span>
                          優先度
                        </span>

                        <strong>
                          {priorityLabel(
                            task.priority
                          )}
                        </strong>
                      </div>


                      <div>
                        <span>
                          出典
                        </span>

                        <strong>
                          Slack
                        </strong>
                      </div>

                    </div>


                    <div
                      className="project-actions"
                      style={{
                        marginTop:
                          "16px",
                      }}
                    >
                      <button
                        className="secondary-button"
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
                          === task.id
                          ? "取得中..."
                          : sourceIsOpen
                          ? "Slack出典を閉じる"
                          : "Slack出典を見る"}
                      </button>
                    </div>


                    {sourceIsOpen && (
                      <div
                        style={{
                          marginTop:
                            "16px",

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
                            Slack出典を読み込んでいます。
                          </p>

                        ) : !source.found ? (

                          <p>
                            元のSlackメッセージを確認できませんでした。
                          </p>

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
                                  ?? "チャンネル不明"}
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
                                ※ このSlackメッセージは編集されています。
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


                    {isEditing &&
                      draft && (

                      <div
                        className="modal-form"
                        style={{
                          marginTop:
                            "20px",
                        }}
                      >

                        <label
                          className="form-field"
                        >
                          <span>
                            Task名
                            <em>
                              必須
                            </em>
                          </span>


                          <input
                            value={
                              draft.title
                            }
                            onChange={(
                              event
                            ) =>
                              updateDraft(
                                task.id,
                                "title",
                                event
                                  .target
                                  .value
                              )
                            }
                          />
                        </label>


                        <label
                          className="form-field"
                        >
                          <span>
                            詳細
                            <small>
                              任意
                            </small>
                          </span>


                          <textarea
                            value={
                              draft.description
                            }
                            onChange={(
                              event
                            ) =>
                              updateDraft(
                                task.id,
                                "description",
                                event
                                  .target
                                  .value
                              )
                            }
                          />
                        </label>


                        <div
                          className="form-grid-two"
                        >

                          <label
                            className="form-field"
                          >
                            <span>
                              Project
                            </span>


                            <select
                              value={
                                draft.projectId
                              }
                              onChange={(
                                event
                              ) =>
                                updateDraft(
                                  task.id,
                                  "projectId",
                                  event
                                    .target
                                    .value
                                )
                              }
                            >

                              <option
                                value=""
                              >
                                Projectなし
                              </option>


                              {projects.map(
                                (
                                  item
                                ) => (
                                  <option
                                    key={
                                      item.id
                                    }
                                    value={
                                      item.id
                                    }
                                  >
                                    {
                                      item.name
                                    }
                                  </option>
                                )
                              )}

                            </select>

                          </label>


                          <label
                            className="form-field"
                          >
                            <span>
                              優先度
                            </span>


                            <select
                              value={
                                draft.priority
                              }
                              onChange={(
                                event
                              ) =>
                                updateDraft(
                                  task.id,
                                  "priority",
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
                                    key={
                                      priority
                                    }
                                    value={
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

                        </div>


                        <label
                          className="form-field"
                        >
                          <span>
                            期限
                            <small>
                              任意
                            </small>
                          </span>


                          <input
                            type="date"
                            value={
                              draft.dueAt
                            }
                            onChange={(
                              event
                            ) =>
                              updateDraft(
                                task.id,
                                "dueAt",
                                event
                                  .target
                                  .value
                              )
                            }
                          />
                        </label>

                      </div>
                    )}


                    <div
                      className="project-actions"
                      style={{
                        gap:
                          "8px",

                        marginTop:
                          "20px",

                        display:
                          "flex",

                        flexWrap:
                          "wrap",
                      }}
                    >

                      <button
                        className="secondary-button"
                        disabled={
                          processingId
                          ===
                          task.id
                        }
                        onClick={() =>
                          rejectTask(
                            task.id
                          )
                        }
                      >
                        却下
                      </button>


                      {isEditing ? (

                        <>

                          <button
                            className="secondary-button"
                            disabled={
                              processingId
                              ===
                              task.id
                            }
                            onClick={() =>
                              cancelEditing(
                                task
                              )
                            }
                          >
                            編集をやめる
                          </button>


                          <button
                            className="primary-button"
                            disabled={
                              processingId
                              ===
                              task.id
                            }
                            onClick={() =>
                              approveTask(
                                task,
                                true
                              )
                            }
                          >
                            {processingId
                              ===
                              task.id
                              ? "処理中..."
                              : "修正して承認"}
                          </button>

                        </>

                      ) : (

                        <>

                          <button
                            className="secondary-button"
                            disabled={
                              processingId
                              ===
                              task.id
                            }
                            onClick={() =>
                              startEditing(
                                task
                              )
                            }
                          >
                            内容を修正
                          </button>


                          <button
                            className="primary-button"
                            disabled={
                              processingId
                              ===
                              task.id
                            }
                            onClick={() =>
                              approveTask(
                                task,
                                false
                              )
                            }
                          >
                            {processingId
                              ===
                              task.id
                              ? "処理中..."
                              : "そのまま承認"}
                          </button>

                        </>

                      )}

                    </div>

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
