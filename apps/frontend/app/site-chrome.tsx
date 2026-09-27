"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isDoc = pathname === "/architecture";

  return (
    <div className={`site ${isDoc ? "doc" : ""}`}>
      <header className="site-header">
        <div className="site-header-inner">
          <Link href="/" className="wordmark">
            <span className="dot" aria-hidden="true" />
            Call AI
          </Link>
          <nav className="site-nav">
            <Link href="/" aria-current={pathname === "/" ? "page" : undefined}>
              Demo
            </Link>
            <Link href="/architecture" aria-current={isDoc ? "page" : undefined}>
              Architecture
            </Link>
          </nav>
        </div>
      </header>
      <div className="site-body">{children}</div>
    </div>
  );
}
