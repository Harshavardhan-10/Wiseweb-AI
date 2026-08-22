import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { PageLoader } from "@/components/ui/spinner";
import { TD, TBody, THead, TR, Table, TH } from "@/components/ui/table";
import { ScanStatusBadge } from "@/components/scan/badges";
import { apiClient } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { errMessage } from "@/lib/utils";
import type { Scan, Website } from "@/lib/types";

export function WebsitesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Website | null>(null);
  const [scanning, setScanning] = useState<{ id: number; loading: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const websites = useQuery({ queryKey: ["websites"], queryFn: apiClient.listWebsites });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteWebsite(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["websites"] });
      setDeleteTarget(null);
    },
    onError: (err) => setError(errMessage(err)),
  });

  async function startScan(websiteId: number) {
    setScanning({ id: websiteId, loading: true });
    setError(null);
    try {
      const scan = await apiClient.createScan(websiteId, 3, 50);
      navigate(`/scans/${scan.id}/progress`);
    } catch (err) {
      setError(errMessage(err));
      setScanning(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Websites</h1>
          <p className="mt-1 text-sm text-slate-500">
            Add sites to analyze, then scan them for health scores and findings.
          </p>
        </div>
        <Button asChild>
          <Link to="/websites/new">Add website</Link>
        </Button>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {websites.isLoading && <PageLoader label="Loading websites…" />}

      {websites.isError && (
        <Alert variant="error" title="Failed to load websites">
          Try refreshing the page.
        </Alert>
      )}

      {websites.data && websites.data.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-sm font-medium text-slate-700">No websites yet</p>
            <p className="max-w-sm text-sm text-slate-500">
              Websites are analyzed passively — Wiseweb-AI only fetches public pages.
            </p>
            <Button asChild>
              <Link to="/websites/new">Add your first website</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {websites.data && websites.data.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <THead>
                <TR>
                  <TH>Website</TH>
                  <TH>Type</TH>
                  <TH>Last scan</TH>
                  <TH>Status</TH>
                  <TH className="text-right">Actions</TH>
                </TR>
              </THead>
              <TBody>
                {websites.data.map((website) => (
                  <WebsiteRow
                    key={website.id}
                    website={website}
                    scanning={scanning?.id === website.id && scanning.loading}
                    onScan={() => void startScan(website.id)}
                    onDelete={() => setDeleteTarget(website)}
                  />
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete website"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => {
                if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
              }}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          Delete <strong>{deleteTarget?.name}</strong>? All scans, findings and
          recommendations for this website will be removed.
        </p>
      </Dialog>
    </div>
  );
}

function WebsiteRow({
  website,
  scanning,
  onScan,
  onDelete,
}: {
  website: Website;
  scanning: boolean;
  onScan: () => void;
  onDelete: () => void;
}) {
  const scans = useQuery({
    queryKey: ["website-scans", website.id],
    queryFn: () => apiClient.listWebsiteScans(website.id),
  });
  const latest: Scan | null = scans.data?.items[0] ?? null;

  return (
    <TR>
      <TD>
        <Link to={`/websites/${website.id}`} className="font-medium text-slate-900 hover:text-indigo-600">
          {website.name}
        </Link>
        <div className="mt-0.5 truncate text-xs text-slate-500">{website.url}</div>
      </TD>
      <TD>
        <Badge variant="outline">{website.website_type}</Badge>
      </TD>
      <TD className="text-xs text-slate-500">
        {latest ? formatRelative(latest.started_at) : "Never"}
      </TD>
      <TD>
        {latest ? (
          <ScanStatusBadge status={latest.status} />
        ) : (
          <Badge variant="muted">Not scanned</Badge>
        )}
      </TD>
      <TD className="text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={onScan} loading={scanning}>
            Scan
          </Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </TD>
    </TR>
  );
}
