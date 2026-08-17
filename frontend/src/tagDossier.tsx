import { createContext, useContext, useState, type ReactNode } from "react";

// Phase 26.5: globaler State für das Tag-Dossier-Sidepanel, damit jede Komponente, die Tags
// rendert, einen Klick auf einen Tag öffnen kann, ohne Props durchreichen zu müssen (analog
// zu unsavedChanges.tsx).
interface TagDossierContextValue {
  openTags: string[];
  mode: "and" | "or";
  isOpen: boolean;
  openTag: (tag: string) => void;
  addTag: (tag: string) => void;
  removeTag: (tag: string) => void;
  setMode: (mode: "and" | "or") => void;
  close: () => void;
}

const TagDossierContext = createContext<TagDossierContextValue>({
  openTags: [],
  mode: "and",
  isOpen: false,
  openTag: () => {},
  addTag: () => {},
  removeTag: () => {},
  setMode: () => {},
  close: () => {},
});

export function TagDossierProvider({ children }: { children: ReactNode }) {
  const [openTags, setOpenTags] = useState<string[]>([]);
  const [mode, setModeState] = useState<"and" | "or">("and");
  const [isOpen, setIsOpen] = useState(false);

  const value: TagDossierContextValue = {
    openTags,
    mode,
    isOpen,
    openTag: (tag) => {
      setOpenTags([tag]);
      setModeState("and");
      setIsOpen(true);
    },
    addTag: (tag) => {
      setOpenTags((prev) => (prev.includes(tag) ? prev : [...prev, tag]));
      setIsOpen(true);
    },
    removeTag: (tag) => {
      setOpenTags((prev) => {
        const next = prev.filter((t) => t !== tag);
        if (next.length === 0) setIsOpen(false);
        return next;
      });
    },
    setMode: setModeState,
    close: () => setIsOpen(false),
  };

  return <TagDossierContext.Provider value={value}>{children}</TagDossierContext.Provider>;
}

export function useTagDossier() {
  return useContext(TagDossierContext);
}
