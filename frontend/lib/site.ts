export const site = {
  name: "Code Archaeologist",
  event: "DevJams '26",
  githubUrl:
    process.env.NEXT_PUBLIC_GITHUB_REPO_URL ??
    "https://github.com/jayansh-work/code-archaeologist-v2",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
  maxCommits: 30,
} as const;
