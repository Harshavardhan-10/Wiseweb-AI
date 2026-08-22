import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Table, TBody, THead, TR, TD, TH } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { scoreTone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { errMessage } from "@/lib/utils";
import { CATEGORY_LABELS, type Comparison, type Category, type Website } from "@/lib/types";

export function ComparisonsPage() {
  const [primaryId, setPrimaryId] = useState<number | null>(null);
  const [selectedWebsites, setSelectedWebsites] = useState<Set<number>>(new Set());
  const [selectedCompetitors, setSelectedCompetitors] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [compName, setCompName] = useState("");
  const [compUrl, setCompUrl] = useState("");
  const [deleteWebsiteTarget, setDeleteWebsiteTarget] = useState<Website | null>(null);
  const queryClient = useQueryClient();

  const websites = useQuery({ queryKey: ["websites"], queryFn: apiClient.listWebsites });

  const competitors = useQuery({
    queryKey: ["competitors", primaryId],
    queryFn: () => apiClient.listCompetitors(primaryId!),
    enabled: primaryId !== null,
  });

  const competitorUrls = new Set(competitors.data?.map((c) => c.normalized_url) ?? []);

  const otherWebsites =
    websites.data?.filter((w) => w.id !== primaryId && !competitorUrls.has(w.normalized_url)) ??
    [];

  const addCompetitor = useMutation({
    mutationFn: () => apiClient.addCompetitor(primaryId!, compName.trim(), compUrl.trim()),
    onSuccess: async () => {
      setAddOpen(false);
      setCompName("");
      setCompUrl("");
      await queryClient.invalidateQueries({ queryKey: ["competitors", primaryId] });
    },
    onError: (err) => setError(errMessage(err)),
  });

  const deleteCompetitor = useMutation({
    mutationFn: (competitorId: number) =>
      apiClient.deleteCompetitor(primaryId!, competitorId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["competitors", primaryId] });
    },
    onError: (err) => setError(errMessage(err)),
  });

  const deleteWebsite = useMutation({
    mutationFn: (id: number) => apiClient.deleteWebsite(id),
    onSuccess: async (_data, id) => {
      setDeleteWebsiteTarget(null);
      setSelectedWebsites((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      if (id === primaryId) {
        setPrimaryId(null);
        setSelectedCompetitors(new Set());
      }
      await queryClient.invalidateQueries({ queryKey: ["websites"] });
    },
    onError: (err) => setError(errMessage(err)),
  });

  const compare = useMutation({
    mutationFn: () =>
      apiClient.compare(primaryId!, [...selectedCompetitors], [...selectedWebsites]),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["websites"] });
    },
    onError: (err) => setError(errMessage(err)),
  });

  const comparison: Comparison | undefined = compare.data;

  function toggleWebsite(id: number) {
    setSelectedWebsites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleCompetitor(id: number) {
    setSelectedCompetitors((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Comparisons</h1>
        <p className="mt-1 text-sm text-slate-500">
          Compare your website against competitors. Competitors are analyzed
          passively and may be scanned in the background.
        </p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      <Card>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="primary">Your website</Label>
              <Select
                id="primary"
                value={primaryId ?? ""}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setPrimaryId(Number.isFinite(v) && v > 0 ? v : null);
                  setSelectedWebsites(new Set());
                  setSelectedCompetitors(new Set());
                }}
              >
                <option value="">Select a website</option>
                {websites.data?.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                size="sm"
                disabled={primaryId === null}
                onClick={() => setAddOpen(true)}
              >
                Add competitor
              </Button>
            </div>
          </div>

          {(otherWebsites.length > 0 || (competitors.data && competitors.data.length > 0)) && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Select competitors to compare
              </p>
              {otherWebsites.map((w) => (
                <div
                  key={`w-${w.id}`}
                  className="flex items-center gap-3 rounded-md border border-slate-200 px-3 py-2 hover:bg-slate-50"
                >
                  <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selectedWebsites.has(w.id)}
                      onChange={() => toggleWebsite(w.id)}
                      className="size-4 rounded border-slate-300 accent-indigo-600"
                    />
                    <span className="text-sm font-medium text-slate-800">{w.name}</span>
                    <span className="truncate text-xs text-slate-500">{w.normalized_url}</span>
                  </label>
                  <button
                    type="button"
                    title="Delete website"
                    disabled={deleteWebsite.isPending}
                    onClick={() => setDeleteWebsiteTarget(w)}
                    className="ml-auto rounded p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                  >
                    <svg
                      className="size-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              ))}
              {competitors.data?.map((c) => (
                <div
                  key={`c-${c.id}`}
                  className="flex items-center gap-3 rounded-md border border-slate-200 px-3 py-2 hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedCompetitors.has(c.id)}
                    onChange={() => toggleCompetitor(c.id)}
                    className="size-4 rounded border-slate-300 accent-indigo-600"
                  />
                  <span className="text-sm font-medium text-slate-800">{c.name}</span>
                  <span className="truncate text-xs text-slate-500">{c.normalized_url}</span>
                  <button
                    type="button"
                    title="Delete competitor"
                    disabled={deleteCompetitor.isPending}
                    onClick={() => deleteCompetitor.mutate(c.id)}
                    className="ml-auto rounded p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                  >
                    <svg
                      className="size-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2">
            <Button
              loading={compare.isPending}
              disabled={
                primaryId === null ||
                (selectedWebsites.size === 0 && selectedCompetitors.size === 0)
              }
              onClick={() => compare.mutate()}
            >
              Compare
            </Button>
            {compare.isPending && (
              <span className="text-xs text-slate-500">
                Analyzing competitors (this can take a minute)…
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {comparison && <ComparisonResults comparison={comparison} />}

      <Dialog
        open={deleteWebsiteTarget !== null}
        onClose={() => setDeleteWebsiteTarget(null)}
        title="Delete website"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteWebsiteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={deleteWebsite.isPending}
              onClick={() => {
                if (deleteWebsiteTarget) deleteWebsite.mutate(deleteWebsiteTarget.id);
              }}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          Delete <strong>{deleteWebsiteTarget?.name}</strong>? All scans, findings and
          recommendations for this website will be removed.
        </p>
      </Dialog>

      <Dialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Add competitor"
        footer={
          <>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={addCompetitor.isPending}
              disabled={!compName.trim() || !compUrl.trim()}
              onClick={() => addCompetitor.mutate()}
            >
              Add
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="cname">Name</Label>
            <Input
              id="cname"
              value={compName}
              onChange={(e) => setCompName(e.target.value)}
              placeholder="Acme Competitor"
            />
          </div>
          <div>
            <Label htmlFor="curl">URL</Label>
            <Input
              id="curl"
              value={compUrl}
              onChange={(e) => setCompUrl(e.target.value)}
              placeholder="https://competitor.example"
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
}

function ComparisonResults({ comparison }: { comparison: Comparison }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Score comparison</CardTitle>
          <CardDescription>Health scores by category across sites.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <THead>
              <TR>
                <TH>Site</TH>
                {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
                  <TH key={c} className="text-right">
                    {CATEGORY_LABELS[c]}
                  </TH>
                ))}
                <TH className="text-right">Overall</TH>
              </TR>
            </THead>
            <TBody>
              {comparison.sites.map((site, i) => {
                const overall = site.scores.OVERALL ?? site.scores.overall;
                const tone = scoreTone(overall as number | null | undefined);
                return (
                  <TR key={i}>
                    <TD>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900">{site.name}</span>
                        {site.is_self && (
                          <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-600">
                            YOU
                          </span>
                        )}
                        {site.is_demo && (
                          <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600">
                            DEMO
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500">{site.url}</div>
                    </TD>
                    {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => {
                      const s = site.scores[c];
                      const t = scoreTone(s as number | null | undefined);
                      return (
                        <TD key={c} className="text-right">
                          <span className={cn("text-sm font-medium", t.text)}>
                            {s === null || s === undefined ? "—" : Math.round(s)}
                          </span>
                        </TD>
                      );
                    })}
                    <TD className={cn("text-right text-sm font-semibold", tone.text)}>
                      {overall === null || overall === undefined
                        ? "—"
                        : Math.round(overall as number)}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        </CardContent>
      </Card>

      {comparison.ai_explanation && (
        <Card className="border-indigo-100 bg-gradient-to-br from-indigo-50/60 to-white">
          <CardContent className="py-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
              AI analysis
            </p>
            <p className="mt-2 text-sm leading-relaxed text-slate-700">
              {comparison.ai_explanation}
            </p>
          </CardContent>
        </Card>
      )}

      {comparison.gaps && Object.keys(comparison.gaps).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Competitive gaps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(comparison.gaps).map(([category, gap]) => {
              const behind = (gap.gap ?? 0) < 0;
              return (
                <div key={category}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-800">
                      {CATEGORY_LABELS[category as Category] ?? category}
                    </p>
                    {gap.gap !== null && gap.gap !== undefined && (
                      <span
                        className={cn(
                          "text-sm font-semibold",
                          behind ? "text-red-600" : "text-emerald-600"
                        )}
                      >
                        {gap.gap > 0 ? "+" : ""}
                        {gap.gap}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    You: {gap.you ?? "—"} · Competitor: {gap.competitor ?? "—"}
                  </p>
                  {gap.explanation && (
                    <p className="mt-1 text-sm text-slate-600">{gap.explanation}</p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
