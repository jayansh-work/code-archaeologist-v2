export function validateGithubRepoUrl(raw: string): string | null {
  const text = raw.trim();
  if (!text) {
    return "A GitHub repository URL is required.";
  }

  let parsed: URL;
  try {
    parsed = new URL(text);
  } catch {
    return "Enter a URL like https://github.com/owner/repository";
  }

  if (parsed.protocol !== "https:") {
    return "Only HTTPS GitHub repository URLs are supported.";
  }

  if (parsed.hostname.toLowerCase() !== "github.com") {
    return "Only public GitHub repositories are supported.";
  }

  if (parsed.username || parsed.password) {
    return "Repository URLs must not include credentials.";
  }

  if (parsed.search || parsed.hash) {
    return "Repository URL must not include query parameters or fragments.";
  }

  const parts = parsed.pathname.split("/").filter(Boolean);
  if (parts.length !== 2) {
    return "URL must look like https://github.com/owner/repository";
  }

  const owner = parts[0];
  let name = parts[1];
  if (name.toLowerCase().endsWith(".git")) {
    name = name.slice(0, -4);
  }

  const ownerOk = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/.test(owner);
  const nameOk = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/.test(name);
  if (!ownerOk || !nameOk) {
    return "Owner or repository name is invalid.";
  }

  return null;
}
