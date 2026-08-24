"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getOfficer, onAuthChange, type StoredOfficer } from "@/lib/auth";

export function OfficerBadge() {
  const pathname = usePathname();
  const router = useRouter();
  const [officer, setOfficer] = useState<StoredOfficer | null>(null);

  useEffect(() => {
    setOfficer(getOfficer());
    return onAuthChange(() => setOfficer(getOfficer()));
  }, []);

  if (pathname === "/login") return null;

  if (!officer) {
    return (
      <span className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted">
        <span className="h-2 w-2 animate-pulse rounded-full bg-[#34C77B]" />
        SIH 26182 · crypto attribution
      </span>
    );
  }

  function logout() {
    api.logout();
    router.push("/login");
  }

  return (
    <span className="ml-auto flex shrink-0 items-center gap-3 text-[12px]">
      <span className="h-2 w-2 shrink-0 rounded-full bg-[#34C77B]" />
      <span className="hidden whitespace-nowrap font-medium text-heading sm:inline">
        {officer.full_name}
      </span>
      {officer.badge_no && (
        <span className="hidden font-mono text-[11px] text-muted sm:inline">
          {officer.badge_no}
        </span>
      )}
      <button
        onClick={logout}
        className="rounded-btn border border-soft-border px-3 py-1.5 text-[11px] text-muted transition-all hover:bg-surface-lavender hover:text-heading"
      >
        Logout
      </button>
    </span>
  );
}
