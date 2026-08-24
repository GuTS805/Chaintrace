"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.login(username.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center">
      <div className="mb-6 text-center">
        <div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-md border border-accent/50 text-lg text-accent">
          ◆
        </div>
        <h1 className="font-display text-lg font-semibold text-text">
          CHAIN<span className="text-accent">TRACE</span>
        </h1>
        <p className="mt-1 text-xs text-muted">
          Officer sign-in required to access wallet attribution and case data.
        </p>
      </div>

      <form
        onSubmit={submit}
        className="space-y-3 rounded-md border border-border bg-panel p-5 shadow-panel"
      >
        <div>
          <label className="mb-1 block text-[10px] uppercase tracking-widest text-muted">
            Username
          </label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            className="w-full rounded border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] uppercase tracking-widest text-muted">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full rounded border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </div>

        {error && <p className="text-xs text-bad">{error}</p>}

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="w-full rounded border border-accent/50 bg-accent/10 py-2 text-xs uppercase tracking-widest text-accent hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-4 text-center text-[11px] text-muted">
        Demo credentials: <span className="text-text">i4c.analyst</span> /{" "}
        <span className="text-text">Chain@2026</span>
      </p>
    </div>
  );
}
