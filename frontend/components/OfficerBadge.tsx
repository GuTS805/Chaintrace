"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, LogOut, ShieldCheck } from "lucide-react";
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
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="ml-auto flex shrink-0 items-center gap-2 rounded-btn py-1.5 pl-2 pr-2.5 text-[12px] transition-colors hover:bg-surface-lavender">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-soft text-[11px] font-semibold text-primary">
            {officer.full_name.slice(0, 1).toUpperCase()}
          </span>
          <span className="hidden whitespace-nowrap font-medium text-heading sm:inline">
            {officer.full_name}
          </span>
          <ChevronDown size={14} className="hidden shrink-0 text-muted sm:inline" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={10}
          className="z-50 w-56 overflow-hidden rounded-card bg-white p-1.5 shadow-card-hover data-[state=open]:animate-fade-up"
        >
          <div className="flex items-center gap-2 px-3 py-2.5">
            <span className="h-2 w-2 shrink-0 rounded-full bg-[#34C77B]" />
            <div className="min-w-0">
              <div className="truncate text-[13px] font-medium text-heading">{officer.full_name}</div>
              {officer.badge_no && (
                <div className="font-mono text-[11px] text-muted">{officer.badge_no}</div>
              )}
            </div>
          </div>

          <DropdownMenu.Separator className="my-1 h-px bg-soft-border" />

          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-btn px-3 py-2 text-[13px] text-muted outline-none data-[highlighted]:bg-surface-lavender data-[highlighted]:text-heading"
            disabled
          >
            <ShieldCheck size={15} />
            Investigating officer
          </DropdownMenu.Item>

          <DropdownMenu.Item
            onSelect={logout}
            className="flex cursor-pointer items-center gap-2 rounded-btn px-3 py-2 text-[13px] font-medium text-bad-text outline-none data-[highlighted]:bg-bad-fill"
          >
            <LogOut size={15} />
            Logout
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
