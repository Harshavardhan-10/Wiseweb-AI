import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { TD, TBody, THead, TR, Table, TH } from "@/components/ui/table";
import { ConfidencePill, FindingStatusBadge, SeverityBadge } from "@/components/scan/badges";
import { apiClient } from "@/lib/api";
import { errMessage } from "@/lib/utils";
import {
  CATEGORIES,
  FINDING_STATUSES,
  SEVERITIES,
  type Evidence,
  type Finding,
  type FindingStatus,
} from "@/lib/types";

interface Filters {
  category: string;
  severity: string;
  status: string;
}

export function FindingsPage() {
  const { scanId } = useParams();
  const id = Number(scanId);
  const [filters, setFilters] = useState<Filters>({ category: "", severity: "", status: "" });
  const [error, setError] = useState<string | null>(null);

  const findings = useQuery({
    queryKey: ["findings", id, filters],
    queryFn: (ctx) =>
      apiClient.listFindings(
        id,
        {
          category: filters.category || undefined,
          severity: filters.severity || undefined,
          status: filters.status || undefined,
        },
        ctx.signal,
      ),
    enabled: Number.isFinite(id),
  });

  return (
    <div className="space-y-6">
      <Header scanId={id} />
      {error && <Alert variant="error">{error}</Alert>}

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 border-b border-slate-100 pb-4">
          <Select
            className="w-40"
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
          >
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
          <Select
            className="w-36"
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
          >
            <option value="">All severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <Select
            className="w-36"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All statuses</option>
            {FINDING_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <span className="ml-auto text-sm text-slate-500">
            {findings.data?.total ?? 0} finding{findings.data?.total === 1 ? "" : "s"}
          </span>
        </CardContent>
      </Card>

      {findings.isLoading && <PageLoader label="Loading findings…" />}

      {findings.isError && (
        <Alert variant="error" title="Failed to load findings">
          {errMessage(findings.error)}
        </Alert>
      )}

      {findings.data && findings.data.items.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            No findings match the current filters.
          </CardContent>
        </Card>
      )}

      {findings.data && findings.data.items.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <THead>
                <TR>
                  <TH>Finding</TH>
                  <TH>Severity</TH>
                  <TH>Category</TH>
                  <TH>Confidence</TH>
                  <TH>Status</TH>
                  <TH>URL</TH>
                </TR>
              </THead>
              <TBody>
                {findings.data.items.map((finding) => (
                  <FindingRow key={finding.id} finding={finding} onError={setError} />
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Header({ scanId }: { scanId: number }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Findings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Evidence-backed issues discovered during the analysis.
        </p>
      </div>
      <div className="flex gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to={`/scans/${scanId}/overview`}>Overview</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to={`/scans/${scanId}/recommendations`}>Recommendations</Link>
        </Button>
      </div>
    </div>
  );
}

function FindingRow({ finding, onError }: { finding: Finding; onError: (m: string) => void }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const updateStatus = useMutation({
    mutationFn: (status: FindingStatus) => apiClient.updateFindingStatus(finding.id, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
    onError: (err) => onError(errMessage(err)),
  });

  return (
    <>
      <TR className="cursor-pointer" onClick={() => setOpen(!open)}>
        <TD>
          <p className="font-medium text-slate-900">{finding.title}</p>
          <p className="text-xs text-slate-400">{finding.rule_id}</p>
        </TD>
        <TD>
          <SeverityBadge severity={finding.severity} />
        </TD>
        <TD>
          <Badge variant="outline">{finding.category}</Badge>
        </TD>
        <TD>
          <ConfidencePill confidence={finding.confidence} />
        </TD>
        <TD>
          <div className="flex items-center gap-2">
            <FindingStatusBadge status={finding.status} />
          </div>
        </TD>
        <TD>
          <span className="block max-w-48 truncate text-xs text-slate-500">
            {finding.affected_url ?? "—"}
          </span>
        </TD>
      </TR>
      {open && (
        <TR>
          <TD colSpan={6} className="bg-slate-50/60">
            <div className="px-4 py-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <Meta label="Impact" value={finding.impact} />
                  <Meta label="Effort" value={finding.effort} />
                </div>
                <div className="sm:col-span-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Description
                  </p>
                  <p className="mt-1 text-sm text-slate-700">
                    {finding.description ?? "No description."}
                  </p>
                </div>
              </div>

              {finding.evidence.length > 0 && (
                <>
                  <Separator className="my-4" />
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Evidence ({finding.evidence.length})
                  </p>
                  <div className="space-y-2">
                    {finding.evidence.map((e) => (
                      <EvidenceItem key={e.id} evidence={e} />
                    ))}
                  </div>
                </>
              )}

              <div className="mt-4 flex items-center gap-2">
                <label className="text-xs font-medium text-slate-500">Mark as</label>
                <Select
                  className="w-44"
                  value={finding.status}
                  onChange={(e) => updateStatus.mutate(e.target.value as FindingStatus)}
                >
                  {FINDING_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
          </TD>
        </TR>
      )}
    </>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-sm text-slate-600">
      <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}:
      </span>
      {value}
    </p>
  );
}

function EvidenceItem({ evidence }: { evidence: Evidence }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {evidence.evidence_type}
        </span>
        <ConfidencePill confidence={evidence.confidence} />
      </div>
      {evidence.source && (
        <p className="mt-1 break-all font-mono text-xs text-slate-500">{evidence.source}</p>
      )}
      {evidence.value && (
        <p className="mt-1 break-all text-sm text-slate-700">{evidence.value}</p>
      )}
    </div>
  );
}
