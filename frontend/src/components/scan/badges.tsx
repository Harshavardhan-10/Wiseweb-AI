import { Badge } from "@/components/ui/badge";
import type { Priority, ScanStatus, Severity } from "@/lib/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const variant =
    severity === "CRITICAL"
      ? "danger"
      : severity === "HIGH"
        ? "warning"
        : severity === "MEDIUM"
          ? "default"
          : severity === "LOW"
            ? "info"
            : "muted";
  return <Badge variant={variant}>{severity}</Badge>;
}

export function PriorityBadge({ priority }: { priority: Priority | string }) {
  const variant =
    priority === "P0" ? "danger" : priority === "P1" ? "warning" : priority === "P2" ? "default" : "muted";
  return <Badge variant={variant}>{priority}</Badge>;
}

export function FindingStatusBadge({ status }: { status: string }) {
  const variant =
    status === "OPEN"
      ? "danger"
      : status === "IN_PROGRESS"
        ? "info"
        : status === "FIXED" || status === "VERIFIED"
          ? "success"
          : status === "DISMISSED"
            ? "muted"
            : "warning";
  return <Badge variant={variant}>{status}</Badge>;
}

export function ScanStatusBadge({ status }: { status: ScanStatus | string }) {
  const variant =
    status === "COMPLETED"
      ? "success"
      : status === "FAILED"
        ? "danger"
        : status === "CANCELLED"
          ? "muted"
          : ["QUEUED", "CRAWLING", "ANALYZING", "AI_PROCESSING"].includes(status)
            ? "info"
            : "default";
  return <Badge variant={variant}>{status}</Badge>;
}

export function ConfidencePill({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const variant = pct >= 80 ? "success" : pct >= 50 ? "default" : "muted";
  return <Badge variant={variant}>{pct}%</Badge>;
}
