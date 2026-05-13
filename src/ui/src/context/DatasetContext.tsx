import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api } from "@/api/client";
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
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDataset, setActiveDatasetState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDatasets()
      .then((data) => {
        setDatasets(data);
        if (data.length > 0) setActiveDatasetState(data[0].id);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

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
