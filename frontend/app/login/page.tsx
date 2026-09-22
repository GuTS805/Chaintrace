"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { api } from "@/lib/api";
import { TraceIllustration } from "@/components/TraceIllustration";
import { Mark } from "@/components/Mark";
import { Button, Eyebrow } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
    <div className="mx-auto grid min-h-[75vh] max-w-6xl items-center gap-12 py-6 lg:grid-cols-[1.1fr_1fr] lg:gap-20">
      <div className="hidden lg:block">
        <Eyebrow tone="accent">The investigation starts here</Eyebrow>
        <h2 className="mt-4 font-display text-[48px] font-bold leading-tight tracking-tight text-heading">Every transaction<br />leaves a <span className="gradient-text">trace.</span></h2>
        <p className="mb-8 mt-4 max-w-md text-base leading-relaxed text-body">Follow it with evidence you can explain. A dedicated workspace for wallet attribution, risk analysis, and case building.</p>
        <TraceIllustration />
      </div>
      <motion.div
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="login-panel glass-panel mx-auto w-full max-w-[440px] rounded-hero border border-soft-border bg-surface p-6 shadow-card sm:p-10"
      >
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 w-fit">
            <Mark size={24} />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-heading">
            Welcome back
          </h1>
          <p className="mt-2 text-[13px] leading-relaxed text-muted">
            Sign in to your investigation workspace.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-5">
          <div>
            <label htmlFor="username" className="mb-2 block text-xs font-medium text-body">Officer username</label>
            <div className="relative">
              <User size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                id="username"
                required
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
                className="w-full rounded-input border border-soft-border bg-surface-lavender py-2.5 pl-9 pr-3 text-sm text-heading outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
              />
            </div>
          </div>
          <div>
            <label htmlFor="password" className="mb-2 block text-xs font-medium text-body">Password</label>
            <div className="relative">
              <Lock size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                id="password"
                required
                placeholder="Enter your password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full rounded-input border border-soft-border bg-surface-lavender py-2.5 pl-9 pr-9 text-sm text-heading outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-heading"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {error && <p role="alert" className="rounded-btn border border-bad-text/20 bg-bad-fill p-3 text-xs text-bad-text">{error}</p>}

          <Button type="submit" variant="primary" disabled={loading || !username || !password} className="w-full">
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 rounded-btn border border-dashed border-soft-border bg-[#0D1025] p-4 text-center text-[12px] leading-relaxed text-muted">
          Demo credentials: <span className="font-mono text-mono">i4c.analyst</span> /{" "}
          <span className="font-mono text-mono">Chain@2026</span>
        </p>
      </motion.div>
    </div>
  );
}
