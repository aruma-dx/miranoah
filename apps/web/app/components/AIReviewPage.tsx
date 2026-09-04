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

  ai_confidence: number | null;
};


type Project = {
  id: string;
  name: string;
};


type Props = {
  apiBaseUrl: string;
};


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
  ).format(
    new Date(value)
  );
}


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
      "手動設定",
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
    loading,
    setLoading,
  ] = useState(true);

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
          setError(null);

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

          setCandidates(
            await reviewsResponse.json()
          );

          setProjects(
            await projectsResponse.json()
          );

        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "エラーが発生しました。"
          );

        } finally {
          setLoading(false);
        }
      },
      [apiBaseUrl]
    );


  useEffect(() => {
    loadData();
  }, [loadData]);


  async function reviewAction(
    taskId: string,
    action:
      | "approve"
      | "reject"
  ) {
    try {
      setProcessingId(
        taskId
      );

      setError(null);
      setSuccess(null);

      const response =
        await fetch(
          `${apiBaseUrl}/api/v1/ai-reviews/${taskId}/${action}`,
          {
            method: "POST",

            credentials:
              "include",
          }
        );

      if (!response.ok) {
        throw new Error(
          action === "approve"
            ? "Taskの承認に失敗しました。"
            : "Task候補の却下に失敗しました。"
        );
      }

      setSuccess(
        action === "approve"
          ? "Taskを承認しました。"
          : "Task候補を却下しました。"
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
          AIがTaskだと判断したものの、
          自動登録には確信が足りない候補を確認します。
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

        ) : candidates.length ===
          0 ? (

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
              (task) => {

                const project =
                  projects.find(
                    (project) =>
                      project.id ===
                      task.project_id
                  );

                return (
                  <article
                    className="project-card"
                    key={task.id}
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
                          期限
                        </span>

                        <strong>
                          {dateLabel(
                            task.due_at
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
                      className="project-actions"
                      style={{
                        gap: "8px",
                      }}
                    >

                      <button
                        className="secondary-button"
                        disabled={
                          processingId
                          === task.id
                        }
                        onClick={() =>
                          reviewAction(
                            task.id,
                            "reject"
                          )
                        }
                      >
                        却下
                      </button>


                      <button
                        className="primary-button"
                        disabled={
                          processingId
                          === task.id
                        }
                        onClick={() =>
                          reviewAction(
                            task.id,
                            "approve"
                          )
                        }
                      >
                        {processingId
                          === task.id
                          ? "処理中..."
                          : "承認してTask化"}
                      </button>

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
