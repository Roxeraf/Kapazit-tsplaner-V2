import type { MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useUnsavedChanges } from "./unsavedChanges";

// Verhindert versehentlichen Verlust ungespeicherter Planungsänderungen (Entwurfsmodus in
// ProjectPlanningTab), wenn über die globale Navigation oder die Projekt-Tab-Leiste eine
// andere Seite aufgerufen wird. Wird von AppShell (Top-Nav) und Tabs (Projekt-Workspace)
// gemeinsam genutzt, da isDirty global über UnsavedChangesProvider geteilt ist.
export function useGuardedNavigate() {
  const { isDirty, setIsDirty } = useUnsavedChanges();
  const navigate = useNavigate();

  return (to: string) => (e: MouseEvent) => {
    if (!isDirty) return;
    e.preventDefault();
    if (window.confirm("Ungespeicherte Änderungen gehen verloren. Trotzdem verlassen?")) {
      setIsDirty(false);
      navigate(to);
    }
  };
}
