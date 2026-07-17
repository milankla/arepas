import { Navigate, Route, Routes } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { SearchProvider } from "@/context/SearchContext";
import { RequireAuth } from "@/auth/RequireAuth";
import { AuthSync } from "@/auth/AuthSync";
import { useUserRole } from "@/auth/useUserRole";
import ExploreDataPage from "@/pages/ExploreDataPage";
import TrainingEvaluationPage from "@/pages/TrainingEvaluationPage";
import InferencePage from "@/pages/InferencePage";

function HomeRoute() {
  const role = useUserRole();
  if (role === "anonymous") return <Navigate to="/inference" replace />;
  return <ExploreDataPage />;
}

function TrainingRoute() {
  const role = useUserRole();
  if (role === "anonymous") return <Navigate to="/inference" replace />;
  if (role === "user") return <Navigate to="/" replace />;
  return (
    <RequireAuth>
      <TrainingEvaluationPage />
    </RequireAuth>
  );
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
        <Route path="/training" element={<TrainingRoute />} />
        {/* OIDC redirect-back route — RequireAuth handles onSigninCallback */}
        <Route path="/callback" element={<InferencePage />} />
      </Routes>
    </SearchProvider>
  );
}
