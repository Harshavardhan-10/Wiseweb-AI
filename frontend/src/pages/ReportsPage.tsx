import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";
import { Tabs } from "@/components/ui/tabs";
import { SeverityBadge } from "@/components/scan/badges";
import { apiClient } from "@/lib/api";
import { errMessage } from "@/lib/utils";
import type { DeveloperReport, ExecutiveReport } from "@/lib/types";

export function ReportsPage() {
  const { scanId } = useParams();
  const id = Number(scanId);
  const [tab, setTab] = useState<"executive" | "developer">("executive");

  const exec = useQuery({
    queryKey: ["executive-report", id],
    queryFn: (ctx) => apiClient.executiveReport(id, ctx.signal),
    enabled: Number.isFinite(id) && tab === "executive",
  });
  const dev = useQuery({
    queryKey: ["developer-report", id],
    queryFn: (ctx) => apiClient.developerReport(id, ctx.signal),
    enabled: Number.isFinite(id) && tab === "developer",
  });

  const loading = tab === "executive" ? exec.isLoading : dev.isLoading;
  const error = tab === "executive" ? exec.error : dev.error;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Reports</h1>
          <p className="mt-1 text-sm text-slate-500">
            Shareable summaries for stakeholders and developers.
          </p>
        </div>
        <div className="flex gap-2 no-print">
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            Print / save PDF
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/scans/${id}/overview`}>Back to overview</Link>
          </Button>
        </div>
      </div>

      <Tabs
        tabs={[
          { value: "executive", label: "Executive" },
          { value: "developer", label: "Developer" },
        ]}
        value={tab}
        onChange={setTab}
      />

      {loading && <PageLoader label="Building report…" />}

      {error && (
        <Alert variant="error" title="Failed to build report">
          {errMessage(error)}
        </Alert>
      )}

      {tab === "executive" && exec.data && <ExecutiveReportView report={exec.data} />}
      {tab === "developer" && dev.data && <DeveloperReportView report={dev.data} />}
    </div>
  );
}

function ExecutiveReportView({ report }: { report: ExecutiveReport }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
            Executive report
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-900">{report.website.name}</h2>
          <p className="text-sm text-slate-500">{report.website.url}</p>
          <p className="mt-3 text-5xl font-bold text-slate-900">
            {report.overall_score === null ? "—" : Math.round(report.overall_score)}
            <span className="text-lg text-slate-400">/100</span>
          </p>
        </CardContent>
      </Card>

      {report.summary.headline && (
        <Card>
          <CardContent className="space-y-3 py-5">
            <p className="text-base font-semibold text-slate-900">{report.summary.headline}</p>
            {report.summary.executive_summary && (
              <p className="text-sm leading-relaxed text-slate-600">
                {report.summary.executive_summary}
              </p>
            )}
            {report.summary.top_risks.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-500">
                  Top risks
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {report.summary.top_risks.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.summary.biggest_opportunities.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-600">
                  Biggest opportunities
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {report.summary.biggest_opportunities.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.summary.roadmap.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-500">
                  Recommended roadmap
                </p>
                <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
                  {report.summary.roadmap.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top findings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.top_risks.length === 0 && (
              <p className="text-sm text-slate-500">No critical or high-risk findings.</p>
            )}
            {report.top_risks.map((risk, i) => (
              <div key={i} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-700">{risk.title}</span>
                <SeverityBadge severity={risk.severity} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top recommendations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.top_recommendations.length === 0 && (
              <p className="text-sm text-slate-500">None.</p>
            )}
            {report.top_recommendations.map((rec, i) => (
              <div key={i} className="flex items-start justify-between gap-3 text-sm">
                <span className="text-slate-700">{rec.title}</span>
                <Badge variant="default">{rec.priority}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DeveloperReportView({ report }: { report: DeveloperReport }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>
            {report.website.name} — developer report
          </CardTitle>
          <CardDescription>
            {report.findings_count} findings · {report.metrics.pages_analyzed} pages analyzed ·{" "}
            {report.technologies.length} technologies detected
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Technologies
          </p>
          <div className="flex flex-wrap gap-2">
            {report.technologies.length === 0 && (
              <span className="text-sm text-slate-500">None detected.</span>
            )}
            {report.technologies.map((t, i) => (
              <Badge key={i} variant="outline">
                {t.name} · {t.category}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {report.findings.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-slate-500">
            No findings in this scan.
          </CardContent>
        </Card>
      )}

      {report.findings.map((finding) => (
        <Card key={finding.id}>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>{finding.title}</CardTitle>
              <div className="flex items-center gap-2">
                <SeverityBadge severity={finding.severity} />
                <Badge variant="outline">{finding.category}</Badge>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <span>Rule: {finding.rule_id}</span>
              <span>·</span>
              <span>Confidence: {Math.round(finding.confidence * 100)}%</span>
              <span>·</span>
              <span>
                {finding.impact.toLowerCase()} impact / {finding.effort.toLowerCase()} effort
              </span>
              {finding.affected_url && (
                <>
                  <span>·</span>
                  <span className="truncate">{finding.affected_url}</span>
                </>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {finding.description && (
              <p className="text-sm text-slate-700">{finding.description}</p>
            )}
            {finding.evidence.length > 0 && (
              <>
                <Separator />
                {finding.evidence.map((e, i) => (
                  <div key={i} className="rounded-md bg-slate-50 px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {e.type}
                    </p>
                    {e.source && (
                      <p className="mt-0.5 break-all font-mono text-xs text-slate-500">{e.source}</p>
                    )}
                    {e.value && (
                      <p className="mt-0.5 break-all text-sm text-slate-700">{e.value}</p>
                    )}
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
