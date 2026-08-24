"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Mark } from "@/components/Mark";
import { Button, Eyebrow } from "@/components/ui";

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
    <div className="mx-auto flex min-h-[70vh] max-w-[360px] flex-col justify-center">
      <div className="mb-10 text-center">
        <div className="mx-auto mb-5 grid h-11 w-11 place-items-center rounded-lg border border-border bg-panel">
          <Mark size={22} />
        </div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text">
          CHAIN<span className="text-accent">TRACE</span>
        </h1>
        <p className="mt-2 text-[13px] leading-relaxed text-muted">
          Officer sign-in required to access wallet attribution and case data.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-5">
        <div>
          <Eyebrow className="mb-2">Username</Eyebrow>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            className="w-full rounded-md border border-border bg-panel2 px-3 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
          />
        </div>
        <div>
          <Eyebrow className="mb-2">Password</Eyebrow>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full rounded-md border border-border bg-panel2 px-3 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
          />
        </div>

        {error && <p className="text-xs text-bad">{error}</p>}

        <Button type="submit" variant="primary" disabled={loading || !username || !password} className="w-full">
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="mt-8 text-center text-[12px] text-dim">
        Demo credentials: <span className="text-muted">i4c.analyst</span> /{" "}
        <span className="text-muted">Chain@2026</span>
      </p>
    </div>
  );
}
