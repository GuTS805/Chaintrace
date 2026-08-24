"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getToken, onAuthChange } from "@/lib/auth";

/** Redirects to /login when no officer session is present. Also reacts to a
 * session being cleared mid-visit (e.g. the API layer clears it on a 401). */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    function check() {
      if (pathname === "/login") {
        setReady(true);
        return;
      }
      if (!getToken()) {
        setReady(false);
        router.replace("/login");
      } else {
        setReady(true);
      }
    }
    check();
    return onAuthChange(check);
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-xs text-muted">
        Checking session…
      </div>
    );
  }

  return <>{children}</>;
}
