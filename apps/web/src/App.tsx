import { Navigate, Route, Routes } from "react-router";

import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { ExperimentDetailPage } from "./pages/ExperimentDetailPage";
import { CompareRunsPage } from "./pages/CompareRunsPage";
import { CreateRunPage } from "./pages/CreateRunPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PlatformHealthPage } from "./pages/PlatformHealthPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SignInPage } from "./pages/SignInPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";
import { WorkerDetailPage } from "./pages/WorkerDetailPage";
import { WorkersPage } from "./pages/WorkersPage";

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/platform-health" element={<PlatformHealthPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route
              path="/experiments/:experimentId"
              element={<ExperimentDetailPage />}
            />
            <Route
              path="/experiments/:experimentId/runs/new"
              element={<CreateRunPage />}
            />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/compare" element={<CompareRunsPage />} />
            <Route path="/runs/:runId" element={<RunDetailPage />} />
            <Route path="/workers" element={<WorkersPage />} />
            <Route path="/workers/:workerId" element={<WorkerDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </AuthProvider>
  );
}
