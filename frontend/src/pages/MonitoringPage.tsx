import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { errMessage } from "@/lib/utils";
import type { ScanComparison } from "@/lib/types";

export function MonitoringPage() {
  const { websiteId } = useParams();
  const id = Number(websiteId);
  const [baseId, setBaseId] = useState<number | null>(null);
  const [compareId, setCompareId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

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
  const changes = useQuery({
    queryKey: ["changes", id],
    queryFn: () => apiClient.listChanges(id),
    enabled: Number.isFinite(id),
  });

  const compare = useMutation({
    mutationFn: () => apiClient.compareScans(id, baseId!, compareId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["changes", id] });
      setBaseId(null);
      setCompareId(null);
    },
    onError: (err) => setError(errMessage(err)),
  });

  const completed = (scans.data?.items ?? []).filter((s) => s.status === "COMPLETED");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Change history</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track what changed between scans of{" "}
            <span className="font-medium text-slate-700">{website.data?.name}</span>.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to={`/websites/${id}`}>Back to website</Link>
        </Button>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      <Card>
        <CardHeader>
          <CardTitle>Compare two scans</CardTitle>
          <CardDescription>Pick a baseline and a newer scan.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="w-64">
            <Select
              value={baseId ?? ""}
              onChange={(e) => setBaseId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Baseline scan…</option>
              {completed.map((s) => (
                <option key={s.id} value={s.id}>
                  #{s.id} · {formatDate(s.started_at)}
                </option>
              ))}
            </Select>
          </div>
          <div className="w-64">
            <Select
              value={compareId ?? ""}
              onChange={(e) => setCompareId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Compare with…</option>
              {completed.map((s) => (
                <option key={s.id} value={s.id}>
                  #{s.id} · {formatDate(s.started_at)}
                </option>
              ))}
            </Select>
          </div>
          <Button
            loading={compare.isPending}
            disabled={baseId === null || compareId === null || baseId === compareId}
            onClick={() => compare.mutate()}
          >
            Compare
          </Button>
        </CardContent>
      </Card>

      {changes.isLoading && <PageLoader label="Loading change history…" />}

      {changes.data && changes.data.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            No comparisons recorded yet. Compare two scans above.
          </CardContent>
        </Card>
      )}

      {changes.data &&
        changes.data.map((change) => (
          <ChangeCard key={change.id} change={change} />
        ))}
    </div>
  );
}

function ChangeCard({ change }: { change: ScanComparison }) {
  const counts = countChanges(change.changes);
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Scans #{change.base_scan_id} → #{change.compare_scan_id}
        </CardTitle>
        <CardDescription>{formatDate(change.created_at)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {change.summary && (
          <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {change.summary}
          </p>
        )}
        {counts.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {counts.map(([label, count]) => (
              <span
                key={label}
                className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700"
              >
                {label}: {count}
              </span>
            ))}
          </div>
        )}
        {change.changes && (
          <details className="rounded-md border border-slate-200">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700">
              Raw change data
            </summary>
            <pre className="max-h-96 overflow-auto bg-slate-50 px-3 py-2 font-mono text-xs text-slate-600">
              {JSON.stringify(change.changes, null, 2)}
            </pre>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

function countChanges(changes: Record<string, unknown> | null): [string, number][] {
  if (!changes) return [];
  const result: [string, number][] = [];
  for (const [key, value] of Object.entries(changes)) {
    if (typeof value === "number") {
      result.push([key, value]);
    } else if (Array.isArray(value)) {
      result.push([key, value.length]);
    } else if (value && typeof value === "object") {
      const obj = value as Record<string, unknown>;
      const counts = (["added", "removed", "changed"] as const).filter((k) => k in obj);
      if (counts.length > 0) {
        const total = counts.reduce((acc, k) => acc + (Array.isArray(obj[k]) ? (obj[k] as unknown[]).length : 0), 0);
        result.push([key, total]);
      }
    }
  }
  return result;
}
