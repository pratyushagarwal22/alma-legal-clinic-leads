"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { isAuthenticated } from "@/lib/auth";

/**
 * Guard for internal (auth-only) routes.
 *
 * Every page placed under the `(internal)` route group is wrapped by this
 * layout. The token lives in the browser (localStorage), so the check runs on
 * the client: unauthenticated visitors are redirected to /login with a `next`
 * param pointing back to the route they tried to reach. Nothing is rendered
 * until the check passes, avoiding a flash of protected content.
 */
export default function InternalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      setAllowed(true);
      return;
    }
    const next = encodeURIComponent(pathname || "/");
    router.replace(`/login?next=${next}`);
  }, [pathname, router]);

  if (!allowed) return null;

  return <>{children}</>;
}
