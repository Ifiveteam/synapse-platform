import { createBrowserRouter, Navigate } from "react-router-dom";

import { ShellLayout } from "@/components/shell/ShellLayout";
import { AgentDetailPage } from "@/pages/agents/AgentDetailPage";
import { IndexerPage } from "@/pages/agents/IndexerPage";
import { NavigatorPage } from "@/pages/agents/NavigatorPage";
import { ProfilerPage } from "@/pages/agents/ProfilerPage";
import { TrendPostDetailPage } from "@/pages/agents/aggregator/TrendPostDetailPage";
import { TrendPostsPage } from "@/pages/agents/aggregator/TrendPostsPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { AnalysisDetailPage } from "@/pages/AnalysisDetailPage";
import { DownloadPage } from "@/pages/DownloadPage";
import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ScrapDetailPage } from "@/pages/ScrapDetailPage";
import { ScrapPage } from "@/pages/ScrapPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SetupPage } from "@/pages/SetupPage";
import { TrendDetailPage } from "@/pages/TrendDetailPage";
import { ROUTES } from "@/routes";

export const router = createBrowserRouter([
  {
    element: <ShellLayout />,
    children: [
      { path: ROUTES.home, element: <HomePage /> },
      { path: ROUTES.myAnalyses, element: <MyAnalysesPage /> },
      { path: "/me/analyses/:id", element: <AnalysisDetailPage /> },
      { path: ROUTES.idealManagement, element: <IdealManagementPage /> },
      { path: ROUTES.trends, element: <TrendDetailPage /> },
      { path: ROUTES.scraps, element: <ScrapPage /> },
      { path: "/me/scraps/:id", element: <ScrapDetailPage /> },
      { path: ROUTES.settings, element: <SettingsPage /> },
      { path: ROUTES.download, element: <DownloadPage /> },
      { path: ROUTES.login, element: <LoginPage /> },
      { path: ROUTES.setup, element: <SetupPage /> },
      { path: ROUTES.profiler, element: <ProfilerPage /> },
      { path: ROUTES.navigator, element: <NavigatorPage /> },
      { path: ROUTES.indexer, element: <IndexerPage /> },
      { path: "/agents/:slug", element: <AgentDetailPage /> },
      { path: "/agents/:slug/posts", element: <TrendPostsPage /> },
      { path: "/agents/:slug/posts/:postId", element: <TrendPostDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  { path: "*", element: <Navigate to={ROUTES.home} replace /> },
]);
