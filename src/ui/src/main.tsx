import { CssBaseline } from "@mui/material";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "react-oidc-context";
import App from "./App";
import { DatasetProvider } from "./context/DatasetContext";
import { oidcConfig } from "./auth/config";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider {...oidcConfig}>
      <BrowserRouter>
        <DatasetProvider>
          <CssBaseline />
          <App />
        </DatasetProvider>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>
);
