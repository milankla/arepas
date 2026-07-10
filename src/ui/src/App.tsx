import { Route, Routes } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { SearchProvider } from "@/context/SearchContext";
import { RequireAuth } from "@/auth/RequireAuth";
import { AuthSync } from "@/auth/AuthSync";
import ExploreDataPage from "@/pages/ExploreDataPage";
import TrainingEvaluationPage from "@/pages/TrainingEvaluationPage";
import InferencePage from "@/pages/InferencePage";

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
          element={
            <RequireAuth>
              <ExploreDataPage />
            </RequireAuth>
          }
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
