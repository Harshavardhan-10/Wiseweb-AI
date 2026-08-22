import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { ScanStatusBadge } from "@/components/scan/badges";
import { apiClient } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { errMessage } from "@/lib/utils";
import { RUNNING_SCAN_STATUSES, type ScanProgress } from "@/lib/types";

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    QUEUED: "Queued — waiting for a worker",
    INITIALIZING: "Initializing scan",
    CRAWLING: "Crawling the website",
    ANALYZING_ARCHITECTURE: "Analyzing architecture",
    ANALYZING_SECURITY: "Analyzing security",
    ANALYZING_PERFORMANCE: "Analyzing performance",
    ANALYZING_ACCESSIBILITY: "Analyzing accessibility",
    ANALYZING_PRIVACY: "Analyzing privacy",
    ANALYZING_SEO: "Analyzing SEO",
    ANALYZING_CONTENT: "Analyzing content",
    ANALYZING_UX: "Analyzing UX",
    AI_CORRELATION: "Correlating findings",
    AI_RECOMMENDATIONS: "Generating recommendations",
    AI_SUMMARY: "Writing summary",
    FINALIZING: "Finalizing results",
    COMPLETED: "Completed",
  };
  return map[stage] ?? stage;
}

export function ScanProgressPage() {
  const { scanId } = useParams();
  const id = Number(scanId);
  const navigate = useNavigate();
  const [cancelled, setCancelled] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const progress = useQuery({
    queryKey: ["scan-progress", id],
    queryFn: (ctx) => apiClient.scanProgress(id, ctx.signal),
    enabled: Number.isFinite(id),
    refetchInterval: (query) => {
      const scan = query.state.data as ScanProgress | undefined;
      return scan && RUNNING_SCAN_STATUSES.includes(scan.status) ? 2000 : false;
    },
  });

  const scan = progress.data;
  const running = scan ? RUNNING_SCAN_STATUSES.includes(scan.status) : false;

  useEffect(() => {
    if (scan?.status === "COMPLETED") {
      const t = setTimeout(() => navigate(`/scans/${id}/overview`, { replace: true }), 1200);
      return () => clearTimeout(t);
    }
  }, [scan?.status, id, navigate]);

  async function cancelScan() {
    setCancelError(null);
    try {
      await apiClient.cancelScan(id);
      setCancelled(true);
    } catch (err) {
      setCancelError(errMessage(err));
    }
  }

  if (progress.isLoading) return <PageLoader label="Loading scan…" />;

  if (progress.isError || !scan) {
    return (
      <div className="space-y-4">
        <Alert variant="error" title="Couldn't load scan">
          {errMessage(progress.error)}
        </Alert>
        <Button asChild variant="outline">
          <Link to="/websites">Back to websites</Link>
        </Button>
      </div>
    );
  }

  const failed = scan.status === "FAILED";
  const done = scan.status === "COMPLETED" || scan.status === "CANCELLED";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Scan #{scan.id}</h1>
          <p className="mt-1 text-sm text-slate-500">
            Website #{scan.website_id} · started {formatDate(scan.started_at)}
          </p>
        </div>
        <ScanStatusBadge status={cancelled ? "CANCELLED" : scan.status} />
      </div>

      {failed && (
        <Alert variant="error" title="Scan failed">
          {scan.error_message ?? "No error details were recorded."}
        </Alert>
      )}

      {cancelled && (
        <Alert variant="warning">This scan was cancelled. No results were produced.</Alert>
      )}

      {cancelError && <Alert variant="error">{cancelError}</Alert>}

      <Card>
        <CardContent className="space-y-5 py-6">
          <div className="flex items-center gap-4">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">{stageLabel(scan.stage)}</span>
                <span className="text-sm font-semibold text-slate-900">
                  {formatPercent(scan.progress_percent)}
                </span>
              </div>
              <Progress value={scan.progress_percent} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Pages discovered" value={String(scan.pages_discovered)} />
            <Stat label="Pages analyzed" value={String(scan.pages_analyzed)} />
            <Stat
              label="Completed"
              value={scan.completed_at ? formatDate(scan.completed_at) : running ? "In progress" : "—"}
            />
          </div>

          {running && (
            <div className="flex justify-center">
              <Button variant="outline" size="sm" onClick={() => void cancelScan()}>
                Cancel scan
              </Button>
            </div>
          )}

          {done && !failed && !cancelled && (
            <div className="flex justify-center gap-2">
              <Button asChild>
                <Link to={`/scans/${id}/overview`}>View results</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to={`/websites/${scan.website_id}`}>Back to website</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}
