import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { TopBar } from "@/components/layout/TopBar";
import { SearchProvider } from "@/context/SearchContext";
import { RequireAuth } from "@/auth/RequireAuth";
import { AuthSync } from "@/auth/AuthSync";
import { AUTH_ENABLED } from "@/auth/config";
import ExploreDataPage from "@/pages/ExploreDataPage";
import TrainingEvaluationPage from "@/pages/TrainingEvaluationPage";
import InferencePage from "@/pages/InferencePage";

function HomeRoute() {
  const auth = useAuth();

  if (!AUTH_ENABLED) return <ExploreDataPage />;
  if (auth.isLoading) return null;
  if (!auth.isAuthenticated) return <Navigate to="/inference" replace />;
  return <ExploreDataPage />;
}

export default function App() {
  return (
    <SearchProvider>
      <AuthSync />
      <TopBar />
      <Routes>
        {/* Inference: open to anonymous guests */}
        <Route path="/inference" element={<InferencePage />} />
        {/* Explore + Training: require login */}
        <Route
          path="/"
          element={<HomeRoute />}
        />
        <Route
          path="/training"
          element={
            <RequireAuth>
              <TrainingEvaluationPage />
            </RequireAuth>
          }
        />
        {/* OIDC redirect-back route — RequireAuth handles onSigninCallback */}
        <Route path="/callback" element={<InferencePage />} />
      </Routes>
    </SearchProvider>
  );
}
