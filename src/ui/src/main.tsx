import { CssBaseline } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { DatasetProvider } from "./context/DatasetContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <DatasetProvider>
        <CssBaseline />
        <App />
      </DatasetProvider>
    </BrowserRouter>
  </StrictMode>
);
