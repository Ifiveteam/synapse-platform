import { createBrowserRouter, Navigate } from "react-router-dom";

import { ShellLayout } from "@/components/shell/ShellLayout";
import { AgentDetailPage } from "@/pages/agents/AgentDetailPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { AnalysisComparePage } from "@/pages/AnalysisComparePage";
import { AnalysisDetailPage } from "@/pages/AnalysisDetailPage";
import { DownloadPage } from "@/pages/DownloadPage";
import { IdealDetailPage } from "@/pages/IdealDetailPage";
import { IdealSetupPage } from "@/pages/IdealSetupPage";
import { PlaylistPage } from "@/pages/PlaylistPage";
import { MyActivityPage } from "@/pages/MyActivityPage";
import { MyHubPage } from "@/pages/MyHubPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ScrapDetailPage } from "@/pages/ScrapDetailPage";
import { ScrapPage } from "@/pages/ScrapPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { PaymentSuccessPage } from "@/pages/PaymentSuccessPage";
import { UploadPage } from "@/pages/UploadPage";
import { ROUTES } from "@/routes";

export const router = createBrowserRouter([
  {
    element: <ShellLayout />,
    children: [
      { path: ROUTES.home, element: <HomePage /> },
      { path: ROUTES.ME.HOME, element: <MyHubPage /> },
      // 폐기된 목록 페이지 — 옛 링크·북마크는 허브로 리다이렉트
      {
        path: ROUTES.myAnalyses,
        element: <Navigate to={ROUTES.ME.HOME} replace />,
      },
      { path: ROUTES.ME.ACTIVITY, element: <MyActivityPage /> },
      { path: "/me/analyses/compare", element: <AnalysisComparePage /> },
      { path: "/me/analyses/:id", element: <AnalysisDetailPage /> },
      // 폐기된 이상향 관리 목록 페이지 — 옛 링크·북마크는 허브로 리다이렉트
      {
        path: ROUTES.idealManagement,
        element: <Navigate to={ROUTES.ME.HOME} replace />,
      },
      { path: ROUTES.idealSetup, element: <IdealSetupPage /> },
      { path: "/me/ideals/:id", element: <IdealDetailPage /> },
      { path: "/me/playlists", element: <PlaylistPage /> },
      { path: ROUTES.scraps, element: <ScrapPage /> },
      { path: "/me/scraps/:id", element: <ScrapDetailPage /> },
      { path: ROUTES.settings, element: <SettingsPage /> },
      { path: ROUTES.paymentSuccess, element: <PaymentSuccessPage /> },
      // 트렌드 대시보드는 홈(`/`)으로 통합 — 옛 경로 호환
      {
        path: ROUTES.reporterTrendGraph,
        element: <Navigate to={ROUTES.home} replace />,
      },
      { path: ROUTES.download, element: <DownloadPage /> },
      { path: ROUTES.login, element: <LoginPage /> },
      { path: ROUTES.upload, element: <UploadPage /> },
      { path: "/agents/:slug", element: <AgentDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  { path: "*", element: <Navigate to={ROUTES.home} replace /> },
]);
