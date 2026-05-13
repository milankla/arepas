import { Route, Routes } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import ExploreDataPage from "@/pages/ExploreDataPage";
import TrainingEvaluationPage from "@/pages/TrainingEvaluationPage";
import InferencePage from "@/pages/InferencePage";

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<ExploreDataPage />} />
        <Route path="/training" element={<TrainingEvaluationPage />} />
        <Route path="/inference" element={<InferencePage />} />
      </Routes>
    </>
  );
}
