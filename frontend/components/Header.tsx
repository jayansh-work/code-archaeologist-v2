import Link from "next/link";

type HeaderProps = {
  repoLabel?: string;
  current?: "home" | "how" | "architecture";
};

export default function Header({ repoLabel, current = "home" }: HeaderProps) {
  return (
    <header className="site-header">
      <Link href="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 16 16" width="16" height="16">
            <path d="M8 1v4.2" fill="none" stroke="currentColor" strokeWidth="1.25" />
            <circle cx="8" cy="8" r="2.4" fill="none" stroke="currentColor" strokeWidth="1.25" />
            <path d="M8 10.8V15" fill="none" stroke="currentColor" strokeWidth="1.25" />
          </svg>
        </span>
        <span className="brand-name">Code Archaeologist</span>
      </Link>
      <div className="header-right">
        {repoLabel ? (
          <span className="header-repo" title={repoLabel}>
            {repoLabel}
          </span>
        ) : null}
        <nav className="nav" aria-label="Primary">
          <Link href="/how-it-works" aria-current={current === "how" ? "page" : undefined}>
            How it works
          </Link>
          <Link
            href="/architecture"
            aria-current={current === "architecture" ? "page" : undefined}
          >
            Architecture
          </Link>
          <a
            href={
              process.env.NEXT_PUBLIC_GITHUB_REPO_URL ??
              "https://github.com/jayansh-work/code-archaeologist-v2"
            }
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
