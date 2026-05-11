import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { DashboardProvider } from "@/contexts/DashboardContext";
import { DDRDataProvider } from "@/contexts/DDRContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import ResetPassword from "./pages/ResetPassword";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import DemoPage from "./pages/DemoPage";
import AgentLab from "./pages/AgentLab";
import UserProfile from "./pages/UserProfile";
import SearchPage from "./pages/Search";
import NotFound from "./pages/NotFound";
import ConfusionMatrix from "./pages/ConfusionMatrix";
import Observability from "./pages/Observability";
import IntelligenceHub from "./pages/IntelligenceHub";
import GraphExplorer from "./pages/GraphExplorer";
import SixSigmaPage from "./pages/SixSigmaPage";
import IntelligenceInsightsPage from "./pages/IntelligenceInsightsPage";
import DDRMetricEditPage from "./pages/DDRMetricEditPage";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <DashboardProvider>
        <DDRDataProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner theme="dark" />
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/auth" element={<Auth />} />
                <Route path="/reset-password" element={<ResetPassword />} />
                <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/demo" element={<DemoPage />} />
                <Route path="/agent-lab" element={<ProtectedRoute><AgentLab /></ProtectedRoute>} />
                <Route path="/confusion-matrix" element={<ConfusionMatrix />} />
                <Route path="/observability" element={<ProtectedRoute><Observability /></ProtectedRoute>} />
                <Route path="/intelligence" element={<ProtectedRoute><IntelligenceHub /></ProtectedRoute>} />
                <Route path="/graph-explorer" element={<ProtectedRoute><GraphExplorer /></ProtectedRoute>} />
                <Route path="/six-sigma" element={<ProtectedRoute><SixSigmaPage /></ProtectedRoute>} />
                <Route path="/intelligence-insights" element={<ProtectedRoute><IntelligenceInsightsPage /></ProtectedRoute>} />
                <Route path="/ddr-metric-edit" element={<ProtectedRoute><DDRMetricEditPage /></ProtectedRoute>} />
                <Route path="/profile" element={
                  <ProtectedRoute>
                    <UserProfile />
                  </ProtectedRoute>
                } />
                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </BrowserRouter>
          </TooltipProvider>
        </DDRDataProvider>
      </DashboardProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
