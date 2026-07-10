import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useAuth } from "react-oidc-context";
import { api, setAuthToken } from "@/api/client";
import { AUTH_ENABLED } from "@/auth/config";
import type { DatasetInfo } from "@/types";

interface DatasetContextValue {
  datasets: DatasetInfo[];
  activeDataset: string;
  setActiveDataset: (id: string) => void;
  loading: boolean;
  error: string | null;
}

const DatasetContext = createContext<DatasetContextValue | null>(null);

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDataset, setActiveDatasetState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = auth.user?.id_token ?? null;

    if (AUTH_ENABLED) {
      if (auth.isLoading) {
        setLoading(true);
        return;
      }
      if (!auth.isAuthenticated || !token) {
        setAuthToken(null);
        setDatasets([]);
        setActiveDatasetState("");
        setError(null);
        setLoading(false);
        return;
      }
      setAuthToken(token);
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .listDatasets()
      .then((data) => {
        if (cancelled) return;
        setDatasets(data);
        if (data.length > 0) setActiveDatasetState(data[0].id);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [auth.isAuthenticated, auth.isLoading, auth.user?.id_token]);

  const setActiveDataset = useCallback((id: string) => {
    setActiveDatasetState(id);
  }, []);

  return (
    <DatasetContext value={{ datasets, activeDataset, setActiveDataset, loading, error }}>
      {children}
    </DatasetContext>
  );
}

export function useDataset(): DatasetContextValue {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDataset must be used inside DatasetProvider");
  return ctx;
}
