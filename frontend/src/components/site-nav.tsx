"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="site-nav" aria-label="Main navigation">
      <Link href="/" aria-current={pathname === "/" ? "page" : undefined}>
        Workspace
      </Link>
      <Link
        href="/api-flows"
        aria-current={pathname === "/api-flows" ? "page" : undefined}
      >
        API Flows
      </Link>
    </nav>
  );
}
