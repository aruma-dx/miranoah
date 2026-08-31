"use client";

import { useEffect, useState } from "react";

type AuthUser = {
  id: string;
  workspace_id: string;
  slack_user_id: string | null;
  email: string | null;
  display_name: string;
  workspace_role: "ADMIN" | "MANAGER" | "PLAYER";
  is_workspace_owner: boolean;
  is_active: boolean;
};

type AuthPanelProps = {
  apiBaseUrl: string;
};

export default function AuthPanel({
  apiBaseUrl,
}: AuthPanelProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const response = await fetch(
          `${apiBaseUrl}/api/v1/auth/me`,
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
          }
        );

        if (!response.ok) {
          setUser(null);
          return;
        }

        const data = (await response.json()) as AuthUser;

        setUser(data);
      } catch (error) {
        console.error(
          "Failed to load authenticated user:",
          error
        );

        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [apiBaseUrl]);

  function login() {
    window.location.href =
      `${apiBaseUrl}/api/v1/auth/google/login`;
  }

  async function logout() {
    try {
      await fetch(
        `${apiBaseUrl}/api/v1/auth/logout`,
        {
          method: "POST",
          credentials: "include",
        }
      );
    } finally {
      setUser(null);
    }
  }

  if (loading) {
    return (
      <div className="auth-panel">
        <div className="auth-status">
          認証情報を確認中...
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="auth-panel">
        <div>
          <div className="auth-label">
            ACCOUNT
          </div>

          <div className="auth-status">
            未ログイン
          </div>
        </div>

        <button
          className="auth-button"
          onClick={login}
        >
          Googleでログイン
        </button>
      </div>
    );
  }

  return (
    <div className="auth-panel">
      <div className="auth-user">
        <div className="auth-avatar">
          {user.display_name
            .slice(0, 1)
            .toUpperCase()}
        </div>

        <div>
          <div className="auth-name">
            {user.display_name}
          </div>

          <div className="auth-meta">
            <span className="role-badge">
              {user.workspace_role}
            </span>

            {user.email && (
              <span>{user.email}</span>
            )}
          </div>
        </div>
      </div>

      <button
        className="auth-button secondary"
        onClick={logout}
      >
        ログアウト
      </button>
    </div>
  );
}
