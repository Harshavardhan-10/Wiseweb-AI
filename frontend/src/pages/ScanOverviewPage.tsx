import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { SeverityBadge } from "@/components/scan/badges";
import { CategoryScores } from "@/components/scan/CategoryScores";
import { ScoreGauge } from "@/components/scan/ScoreGauge";
import { apiClient } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { errMessage } from "@/lib/utils";

const tabs = [
  { to: "findings", label: "Findings" },
  { to: "recommendations", label: "Recommendations" },
  { to: "architecture", label: "Architecture" },
  { to: "reports", label: "Reports" },
];

export function ScanOverviewPage() {
  const { scanId } = useParams();
  const id = Number(scanId);

  const report = useQuery({
    queryKey: ["executive-report", id],
    queryFn: (ctx) => apiClient.executiveReport(id, ctx.signal),
    enabled: Number.isFinite(id),
  });

  if (report.isLoading) return <PageLoader label="Preparing scan overview…" />;

  if (report.isError || !report.data) {
    return (
      <div className="space-y-4">
        <Alert variant="error" title="Couldn't load scan overview">
          {errMessage(report.error)}
        </Alert>
        <Button asChild variant="outline">
          <Link to="/websites">Back to websites</Link>
        </Button>
      </div>
    );
  }

  const r = report.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {r.website.name} — scan #{r.scan.id}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            <a href={r.website.url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:text-indigo-500">
              {r.website.url}
            </a>{" "}
            · completed {formatDate(r.scan.completed_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <Button key={tab.to} asChild variant="outline" size="sm">
              <Link to={`/scans/${id}/${tab.to}`}>{tab.label}</Link>
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Overall health score</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center py-6">
            <ScoreGauge score={r.overall_score} size="lg" label="Overall health" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Category scores</CardTitle>
            <CardDescription>
              Each category is measured independently from real evidence.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CategoryScores scores={r.scores} />
          </CardContent>
        </Card>
      </div>

      {r.summary.headline && (
        <Card className="border-indigo-100 bg-gradient-to-br from-indigo-50/60 to-white">
          <CardContent className="py-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
              AI summary
            </p>
            <p className="mt-2 text-lg font-medium text-slate-900">{r.summary.headline}</p>
            {r.summary.executive_summary && (
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {r.summary.executive_summary}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top risks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {r.top_risks.length === 0 && (
              <p className="text-sm text-slate-500">No critical or high-risk findings.</p>
            )}
            {r.top_risks.map((risk, i) => (
              <div key={i} className="flex items-start justify-between gap-3">
                <p className="text-sm text-slate-700">{risk.title}</p>
                <SeverityBadge severity={risk.severity} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top recommendations</CardTitle>
            <CardDescription>Ranked by priority score.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {r.top_recommendations.length === 0 && (
              <p className="text-sm text-slate-500">No recommendations yet.</p>
            )}
            {r.top_recommendations.map((rec, i) => (
              <div key={i} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800">{rec.title}</p>
                  <p className="text-xs text-slate-500">
                    {rec.priority} · {rec.impact.toLowerCase()} impact · {rec.effort.toLowerCase()} effort
                  </p>
                </div>
                <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-700">
                  {rec.priority}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
