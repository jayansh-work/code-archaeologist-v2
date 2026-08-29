import { site } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="site-footer">
      {site.name} · {site.event}
    </footer>
  );
}
