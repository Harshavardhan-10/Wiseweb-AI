import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { ConfidencePill, PriorityBadge } from "@/components/scan/badges";
import { apiClient } from "@/lib/api";
import { errMessage } from "@/lib/utils";
import {
  PRIORITIES,
  RECOMMENDATION_STATUSES,
  type Recommendation,
} from "@/lib/types";

export function RecommendationsPage() {
  const { scanId } = useParams();
  const id = Number(scanId);
  const [error, setError] = useState<string | null>(null);

  const recs = useQuery({
    queryKey: ["recommendations", id],
    queryFn: (ctx) => apiClient.listRecommendations(id, {}, ctx.signal),
    enabled: Number.isFinite(id),
  });

  const sorted = recs.data
    ? [...recs.data.items].sort((a, b) => {
        const order = (p: string) => PRIORITIES.indexOf(p as (typeof PRIORITIES)[number]);
        return order(a.priority) - order(b.priority) || b.priority_score - a.priority_score;
      })
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Recommendations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Prioritized actions derived from correlated findings.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={`/scans/${id}/overview`}>Overview</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/scans/${id}/findings`}>Findings</Link>
          </Button>
        </div>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {recs.isLoading && <PageLoader label="Loading recommendations…" />}

      {recs.isError && (
        <Alert variant="error" title="Failed to load recommendations">
          {errMessage(recs.error)}
        </Alert>
      )}

      {recs.data && recs.data.items.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            No recommendations were generated for this scan.
          </CardContent>
        </Card>
      )}

      {sorted.length > 0 && (
        <div className="space-y-4">
          {PRIORITIES.map((priority) => {
            const group = sorted.filter((r) => r.priority === priority);
            if (group.length === 0) return null;
            return (
              <div key={priority} className="space-y-3">
                <div className="flex items-center gap-2">
                  <PriorityBadge priority={priority} />
                  <span className="text-xs uppercase tracking-wide text-slate-400">
                    {group.length} {group.length === 1 ? "item" : "items"}
                  </span>
                </div>
                {group.map((rec) => (
                  <RecommendationCard key={rec.id} rec={rec} onError={setError} />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({
  rec,
  onError,
}: {
  rec: Recommendation;
  onError: (m: string) => void;
}) {
  const queryClient = useQueryClient();

  const updateStatus = useMutation({
    mutationFn: (status: string) => apiClient.updateRecommendationStatus(rec.id, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err) => onError(errMessage(err)),
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <CardTitle>{rec.title}</CardTitle>
          <div className="flex items-center gap-2">
            <ConfidencePill confidence={rec.confidence} />
            <Select
              className="w-36"
              value={rec.status}
              onChange={(e) => updateStatus.mutate(e.target.value)}
            >
              {RECOMMENDATION_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          <Badge variant="outline">{rec.category}</Badge>
          <Badge variant="muted">{rec.impact.toLowerCase()} impact</Badge>
          <Badge variant="muted">{rec.effort.toLowerCase()} effort</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {rec.description && (
          <p className="text-sm leading-relaxed text-slate-700">{rec.description}</p>
        )}
        {rec.root_cause && (
          <div className="rounded-md bg-amber-50 px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              Root cause
            </p>
            <p className="mt-1 text-sm text-amber-900">{rec.root_cause}</p>
          </div>
        )}
        {rec.implementation_guidance && (
          <div className="rounded-md bg-slate-50 px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Implementation guidance
            </p>
            <p className="mt-1 text-sm text-slate-700">{rec.implementation_guidance}</p>
          </div>
        )}
        {rec.finding_ids.length > 0 && (
          <p className="text-xs text-slate-400">
            Linked to {rec.finding_ids.length} finding{rec.finding_ids.length === 1 ? "" : "s"}:{" "}
            {rec.finding_ids.join(", ")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
