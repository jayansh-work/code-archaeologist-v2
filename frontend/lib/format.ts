export function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatRelative(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const delta = Date.now() - date.getTime();
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (delta < hour) {
    const minutes = Math.max(1, Math.round(delta / minute));
    return `${minutes}m ago`;
  }
  if (delta < day) {
    const hours = Math.round(delta / hour);
    return `${hours}h ago`;
  }
  const days = Math.round(delta / day);
  if (days < 45) {
    return `${days}d ago`;
  }
  return formatTimestamp(value);
}

export function formatShortDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function changeTypeLabel(value: string | null): string {
  if (!value) {
    return "M";
  }
  const map: Record<string, string> = {
    added: "A",
    modified: "M",
    deleted: "D",
    renamed: "R",
    copied: "C",
    binary: "B",
    "type-changed": "T",
  };
  return map[value] ?? value.slice(0, 1).toUpperCase();
}

export async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}
