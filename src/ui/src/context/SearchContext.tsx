import { createContext, useContext, useState } from "react";
import type { BuildingSummary } from "@/types";

interface SearchContextValue {
  selectedBuilding: BuildingSummary | null;
  selectBuilding: (b: BuildingSummary | null) => void;
}

const SearchContext = createContext<SearchContextValue>({
  selectedBuilding: null,
  selectBuilding: () => {},
});

export function SearchProvider({ children }: { children: React.ReactNode }) {
  const [selectedBuilding, setSelectedBuilding] = useState<BuildingSummary | null>(null);
  return (
    <SearchContext.Provider value={{ selectedBuilding, selectBuilding: setSelectedBuilding }}>
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  return useContext(SearchContext);
}
