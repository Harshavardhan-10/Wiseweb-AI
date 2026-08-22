import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScanStatusBadge } from "@/components/scan/badges";
import { ScoreGauge } from "@/components/scan/ScoreGauge";
import { apiClient } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { useAuth } from "@/store/auth";
import type { Scan, Website } from "@/lib/types";

interface SiteWithLatest {
  website: Website;
  latestScan: Scan | null;
}

function useSitesWithLatestScans() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async (): Promise<SiteWithLatest[]> => {
      const websites = await apiClient.listWebsites();
      const sites = await Promise.all(
        websites.map(async (website) => {
          try {
            const res = await apiClient.listWebsiteScans(website.id);
            return { website, latestScan: res.items[0] ?? null };
          } catch {
            return { website, latestScan: null };
          }
        }),
      );
      return sites.sort((a, b) => {
        const at = a.latestScan?.started_at ?? "";
        const bt = b.latestScan?.started_at ?? "";
        return bt.localeCompare(at);
      });
    },
  });
}

export function DashboardPage() {
  const { user } = useAuth();
  const sites = useSitesWithLatestScans();

  if (sites.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Welcome back, {user?.full_name?.split(" ")[0] ?? "there"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Here's how your websites are performing.
          </p>
        </div>
        <Button asChild>
          <Link to="/websites/new">Add website</Link>
        </Button>
      </div>

      {sites.data && sites.data.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-sm font-medium text-slate-700">No websites yet</p>
            <p className="max-w-sm text-sm text-slate-500">
              Add your first website to run a passive analysis and get health scores,
              findings, and prioritized recommendations.
            </p>
            <Button asChild>
              <Link to="/websites/new">Add your first website</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {sites.data && sites.data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sites.data.map(({ website, latestScan }, index) => (
            <Card key={website.id}>
              <CardHeader>
                <CardTitle className="truncate">{website.name}</CardTitle>
                <CardDescription className="truncate">
                  <a
                    href={website.normalized_url}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-indigo-600"
                  >
                    {website.normalized_url}
                  </a>
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center gap-5">
                <ScoreGauge score={latestScan?.overall_score} size="sm" />
                <div className="min-w-0 flex-1 space-y-1.5 text-sm">
                  {latestScan ? (
                    <>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-slate-500">Scan #{index + 1}</span>
                        <ScanStatusBadge status={latestScan.status} />
                      </div>
                      <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                        <span>{latestScan.pages_analyzed} pages analyzed</span>
                        <span>{formatRelative(latestScan.started_at)}</span>
                      </div>
                      <div className="pt-1">
                        <Button asChild size="sm" variant="outline" className="w-full">
                          <Link to={`/websites/${website.id}`}>View details</Link>
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-xs text-slate-500">Not scanned yet</p>
                      <Button asChild size="sm" className="w-full">
                        <Link to={`/websites/${website.id}`}>Start analysis</Link>
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {sites.isError && (
        <Card>
          <CardContent className="py-8 text-sm text-red-600">
            Couldn't load your dashboard. Please try again.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
