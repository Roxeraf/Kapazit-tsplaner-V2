import { useTagDossier } from "../tagDossier";

// Phase 26.5: ersetzt die bisherigen reinen <span>#{tag}</span>-Anzeigen - Klick öffnet das
// Tag-Dossier-Sidepanel statt nur lokal zu filtern (siehe tagDossier.tsx).
export default function TagChip({ name }: { name: string }) {
  const { openTag } = useTagDossier();
  return (
    <button
      type="button"
      onClick={() => openTag(name)}
      style={{
        fontSize: "0.75rem",
        color: "var(--blau)",
        border: "none",
        background: "none",
        padding: 0,
        cursor: "pointer",
      }}
    >
      #{name}
    </button>
  );
}
