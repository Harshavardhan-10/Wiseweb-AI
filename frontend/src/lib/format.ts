const dateFmt = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const dayFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return dateFmt.format(d);
}

export function formatDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return dayFmt.format(d);
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "—";
  const diff = Date.now() - d;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDay(iso);
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  return score.toFixed(0);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value)}%`;
}

export function scoreTone(score: number | null | undefined): {
  text: string;
  bg: string;
  bar: string;
  label: string;
} {
  if (score === null || score === undefined) {
    return { text: "text-slate-400", bg: "bg-slate-100", bar: "bg-slate-300", label: "Unmeasured" };
  }
  if (score >= 90) return { text: "text-emerald-600", bg: "bg-emerald-50", bar: "bg-emerald-500", label: "Excellent" };
  if (score >= 75) return { text: "text-emerald-700", bg: "bg-emerald-50", bar: "bg-emerald-500", label: "Good" };
  if (score >= 60) return { text: "text-amber-600", bg: "bg-amber-50", bar: "bg-amber-500", label: "Needs work" };
  return { text: "text-red-600", bg: "bg-red-50", bar: "bg-red-500", label: "Poor" };
}
