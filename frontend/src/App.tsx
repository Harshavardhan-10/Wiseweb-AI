import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/ui/spinner";
import { useAuth } from "@/store/auth";
import { ArchitecturePage } from "@/pages/ArchitecturePage";
import { ComparisonsPage } from "@/pages/ComparisonsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { FindingsPage } from "@/pages/FindingsPage";
import { LoginPage } from "@/pages/LoginPage";
import { MonitoringPage } from "@/pages/MonitoringPage";
import { NewWebsitePage } from "@/pages/NewWebsitePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RecommendationsPage } from "@/pages/RecommendationsPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { ScanOverviewPage } from "@/pages/ScanOverviewPage";
import { ScanProgressPage } from "@/pages/ScanProgressPage";
import { WebsiteDetailPage } from "@/pages/WebsiteDetailPage";
import { WebsitesPage } from "@/pages/WebsitesPage";

function Protected() {
  const { user, initializing } = useAuth();
  if (initializing) return <PageLoader label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<Protected />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/websites" element={<WebsitesPage />} />
        <Route path="/websites/new" element={<NewWebsitePage />} />
        <Route path="/websites/:websiteId" element={<WebsiteDetailPage />} />
        <Route path="/websites/:websiteId/monitoring" element={<MonitoringPage />} />
        <Route path="/scans/:scanId/progress" element={<ScanProgressPage />} />
        <Route path="/scans/:scanId/overview" element={<ScanOverviewPage />} />
        <Route path="/scans/:scanId/findings" element={<FindingsPage />} />
        <Route path="/scans/:scanId/recommendations" element={<RecommendationsPage />} />
        <Route path="/scans/:scanId/architecture" element={<ArchitecturePage />} />
        <Route path="/scans/:scanId/reports" element={<ReportsPage />} />
        <Route path="/comparisons" element={<ComparisonsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
