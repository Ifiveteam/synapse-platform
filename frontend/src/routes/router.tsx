import { createBrowserRouter, Navigate } from "react-router-dom";

import { ShellLayout } from "@/components/shell/ShellLayout";
import { AgentDetailPage } from "@/pages/agents/AgentDetailPage";
import { TrendPostDetailPage } from "@/pages/agents/aggregator/TrendPostDetailPage";
import { TrendPostsPage } from "@/pages/agents/aggregator/TrendPostsPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { AnalysisComparePage } from "@/pages/AnalysisComparePage";
import { AnalysisDetailPage } from "@/pages/AnalysisDetailPage";
import { DownloadPage } from "@/pages/DownloadPage";
import { IdealDetailPage } from "@/pages/IdealDetailPage";
import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { IdealSetupPage } from "@/pages/IdealSetupPage";
import { PlaylistPage } from "@/pages/PlaylistPage";
import { MyActivityPage } from "@/pages/MyActivityPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ScrapDetailPage } from "@/pages/ScrapDetailPage";
import { ScrapPage } from "@/pages/ScrapPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { PaymentSuccessPage } from "@/pages/PaymentSuccessPage";
import { SetupPage } from "@/pages/SetupPage";
import { UploadPage } from "@/pages/UploadPage";
import { TrendDetailPage } from "@/pages/TrendDetailPage";
import { ROUTES } from "@/routes";

export const router = createBrowserRouter([
  {
    element: <ShellLayout />,
    children: [
      { path: ROUTES.home, element: <HomePage /> },
      { path: ROUTES.myAnalyses, element: <MyAnalysesPage /> },
      { path: ROUTES.ME.ACTIVITY, element: <MyActivityPage /> },
      { path: "/me/analyses/compare", element: <AnalysisComparePage /> },
      { path: "/me/analyses/:id", element: <AnalysisDetailPage /> },
      { path: ROUTES.idealManagement, element: <IdealManagementPage /> },
      { path: ROUTES.idealSetup, element: <IdealSetupPage /> },
      { path: "/me/ideals/:id", element: <IdealDetailPage /> },
      { path: "/me/playlists", element: <PlaylistPage /> },
      { path: ROUTES.trends, element: <TrendDetailPage /> },
      { path: ROUTES.scraps, element: <ScrapPage /> },
      { path: "/me/scraps/:id", element: <ScrapDetailPage /> },
      { path: ROUTES.settings, element: <SettingsPage /> },
      { path: ROUTES.paymentSuccess, element: <PaymentSuccessPage /> },
      { path: ROUTES.download, element: <DownloadPage /> },
      { path: ROUTES.login, element: <LoginPage /> },
      { path: ROUTES.upload, element: <UploadPage /> },
      { path: ROUTES.setup, element: <SetupPage /> },
      { path: "/agents/:slug", element: <AgentDetailPage /> },
      { path: "/agents/:slug/posts", element: <TrendPostsPage /> },
      { path: "/agents/:slug/posts/:postId", element: <TrendPostDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  { path: "*", element: <Navigate to={ROUTES.home} replace /> },
]);
