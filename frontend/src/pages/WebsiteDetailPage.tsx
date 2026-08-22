import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageLoader } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { TD, TBody, THead, TR, Table, TH } from "@/components/ui/table";
import { ScanStatusBadge } from "@/components/scan/badges";
import { ScoreGauge } from "@/components/scan/ScoreGauge";
import { CategoryScores } from "@/components/scan/CategoryScores";
import { apiClient } from "@/lib/api";
import { formatDate, formatRelative } from "@/lib/format";
import { errMessage } from "@/lib/utils";
import type { Scan } from "@/lib/types";

const scanNav = [
  { to: "overview", label: "Overview" },
  { to: "findings", label: "Findings" },
  { to: "recommendations", label: "Recommendations" },
  { to: "architecture", label: "Architecture" },
  { to: "reports", label: "Reports" },
];

export function WebsiteDetailPage() {
  const { websiteId } = useParams();
  const id = Number(websiteId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [scanOpen, setScanOpen] = useState(false);
  const [crawlDepth, setCrawlDepth] = useState(3);
  const [pageLimit, setPageLimit] = useState(50);
  const [error, setError] = useState<string | null>(null);

  const website = useQuery({
    queryKey: ["website", id],
    queryFn: () => apiClient.getWebsite(id),
    enabled: Number.isFinite(id),
  });
  const scans = useQuery({
    queryKey: ["website-scans", id],
    queryFn: () => apiClient.listWebsiteScans(id),
    enabled: Number.isFinite(id),
  });

  const monitoring = useMutation({
    mutationFn: (enabled: boolean) => apiClient.setMonitoring(id, enabled),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["website", id] });
    },
    onError: (err) => setError(errMessage(err)),
  });

  const startScan = useMutation({
    mutationFn: () => apiClient.createScan(id, crawlDepth, pageLimit),
    onSuccess: (scan) => {
      setScanOpen(false);
      navigate(`/scans/${scan.id}/progress`);
    },
    onError: (err) => setError(errMessage(err)),
  });

  if (website.isLoading) return <PageLoader label="Loading website…" />;

  if (website.isError || !website.data) {
    return (
      <Alert variant="error" title="Website not found">
        It may have been deleted or you don't have access.
      </Alert>
    );
  }

  const w = website.data;
  const latest: Scan | undefined = scans.data?.items[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-slate-900">{w.name}</h1>
            <Badge variant="outline">{w.website_type}</Badge>
          </div>
          <a
            href={w.normalized_url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-sm text-indigo-600 hover:text-indigo-500"
          >
            {w.normalized_url}
          </a>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={w.monitoring_enabled}
                onChange={(e) => monitoring.mutate(e.target.checked)}
                className="size-3.5 rounded border-slate-300 accent-indigo-600"
              />
              Monitoring
            </label>
            {w.industry && <Badge variant="muted">{w.industry}</Badge>}
            {w.description && <span className="max-w-md truncate">{w.description}</span>}
          </div>
        </div>
        <Button onClick={() => setScanOpen(true)} loading={startScan.isPending}>
          Run new scan
        </Button>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {latest && latest.status === "COMPLETED" && (
        <Card>
          <CardHeader>
            <CardTitle>Latest analysis — scan #{latest.id}</CardTitle>
            <CardDescription>
              Completed {formatDate(latest.completed_at)} · {latest.pages_analyzed} pages
              analyzed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center gap-6">
              <ScoreGauge score={latest.overall_score} size="md" label="Overall health" />
              <div className="min-w-0 flex-1">
                <CategoryScores
                  scores={{
                    SECURITY: latest.security_score,
                    PERFORMANCE: latest.performance_score,
                    ACCESSIBILITY: latest.accessibility_score,
                    PRIVACY: latest.privacy_score,
                    SEO: latest.seo_score,
                    CONTENT: latest.content_score,
                    UX: latest.ux_score,
                    ARCHITECTURE: latest.architecture_score,
                  }}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {scanNav.map((item) => (
                <Button key={item.to} asChild variant="outline" size="sm">
                  <Link to={`/scans/${latest.id}/${item.to}`}>{item.label}</Link>
                </Button>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/websites/${id}/monitoring`)}
              >
                Change history
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {latest && latest.status !== "COMPLETED" && (
        <Card>
          <CardContent className="flex items-center justify-between gap-4 py-4">
            <div className="flex items-center gap-4">
              <ScanStatusBadge status={latest.status} />
              <div className="w-40">
                <Progress value={latest.progress_percent} />
              </div>
              <span className="text-sm text-slate-600">{latest.progress_percent}%</span>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to={`/scans/${latest.id}/progress`}>View scan progress</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Scan history</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {scans.isLoading ? (
            <PageLoader label="Loading scans…" />
          ) : scans.data && scans.data.items.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-slate-500">
              No scans yet. Run your first analysis to see results here.
            </div>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Scan</TH>
                  <TH>Status</TH>
                  <TH>Pages</TH>
                  <TH>Score</TH>
                  <TH>Started</TH>
                  <TH>Completed</TH>
                </TR>
              </THead>
              <TBody>
                {scans.data?.items.map((scan) => (
                  <TR key={scan.id}>
                    <TD>
                      <Link
                        to={`/scans/${scan.id}/overview`}
                        className="font-medium text-indigo-600 hover:text-indigo-500"
                      >
                        #{scan.id}
                      </Link>
                      <span className="ml-2 text-xs text-slate-400">
                        depth {scan.crawl_depth} · {scan.page_limit} pages
                      </span>
                    </TD>
                    <TD>
                      <ScanStatusBadge status={scan.status} />
                    </TD>
                    <TD className="text-slate-600">{scan.pages_analyzed}</TD>
                    <TD className="font-medium text-slate-900">
                      {scan.overall_score === null ? "—" : Math.round(scan.overall_score)}
                    </TD>
                    <TD className="text-xs text-slate-500">{formatRelative(scan.started_at)}</TD>
                    <TD className="text-xs text-slate-500">{formatRelative(scan.completed_at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        title="Run new scan"
        footer={
          <>
            <Button variant="outline" onClick={() => setScanOpen(false)}>
              Cancel
            </Button>
            <Button loading={startScan.isPending} onClick={() => startScan.mutate()}>
              Start scan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Scanning <strong>{w.name}</strong> — a passive, public-only crawl that
            discovers pages and analyzes them against 8 categories.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="depth">Crawl depth (1–5)</Label>
              <Input
                id="depth"
                type="number"
                min={1}
                max={5}
                value={crawlDepth}
                onChange={(e) => setCrawlDepth(Number(e.target.value))}
              />
            </div>
            <div>
              <Label htmlFor="limit">Page limit (1–200)</Label>
              <Input
                id="limit"
                type="number"
                min={1}
                max={200}
                value={pageLimit}
                onChange={(e) => setPageLimit(Number(e.target.value))}
              />
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
