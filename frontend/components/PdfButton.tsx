"use client";

import { useState } from "react";
import { api } from "@/lib/api";

/** A PDF download that goes through fetch (so the auth header attaches) instead
 * of a plain <a href> (which can't carry a custom Authorization header). */
export function PdfButton({
  path,
  className,
  children,
}: {
  path: string;
  className?: string;
  children: React.ReactNode;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setLoading(true);
    setError(null);
    try {
      const { blob, filename } = await api.downloadPdf(path);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button type="button" onClick={download} disabled={loading} className={className}>
        {loading ? "…" : children}
      </button>
      {error && <span className="text-[10px] text-bad">{error}</span>}
    </span>
  );
}
