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
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-good" />
        SIH 26182 · crypto attribution
      </span>
    );
  }

  function logout() {
    api.logout();
    router.push("/login");
  }

  return (
    <span className="ml-auto flex items-center gap-3 text-[10px] uppercase tracking-widest text-muted">
      <span className="h-1.5 w-1.5 rounded-full bg-good" />
      <span className="normal-case tracking-normal text-text">
        {officer.full_name}
      </span>
      {officer.badge_no && <span>{officer.badge_no}</span>}
      <button
        onClick={logout}
        className="rounded border border-border px-2 py-1 hover:border-accent hover:text-accent"
      >
        logout
      </button>
    </span>
  );
}
