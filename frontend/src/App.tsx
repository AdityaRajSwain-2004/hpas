import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./store/auth";
import "./index.css";

import LoginPage    from "./components/auth/LoginPage";
import AppLayout    from "./components/layout/AppLayout";
import Dashboard    from "./components/dashboard/Dashboard";
import Prospects    from "./components/prospects/Prospects";
import Pipeline     from "./components/pipeline/Pipeline";
import WorkflowView from "./components/workflow/WorkflowView";
import HITLQueue    from "./components/hitl/HITLQueue";
import AgentsView   from "./components/agents/AgentsView";
import Campaigns    from "./components/campaigns/Campaigns";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const { initialize } = useAuthStore();
  useEffect(() => { initialize(); }, [initialize]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"  element={<Dashboard />} />
            <Route path="prospects"  element={<Prospects />} />
            <Route path="pipeline"   element={<Pipeline />} />
            <Route path="workflow"   element={<WorkflowView />} />
            <Route path="hitl"       element={<HITLQueue />} />
            <Route path="agents"     element={<AgentsView />} />
            <Route path="campaigns"  element={<Campaigns />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#16191e", color: "#e2e8f0",
            border: "0.5px solid rgba(255,255,255,0.08)",
            fontSize: "13px", borderRadius: "10px",
          },
        }}
      />
    </QueryClientProvider>
  );
}
