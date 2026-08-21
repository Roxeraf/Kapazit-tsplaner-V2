import { useEffect, useState } from "react";
import { api } from "../api/client";

// P12.1 (Tag Experience Completion): an jedem taggbaren Objekt soll der User 1) einen
// vorhandenen Tag suchen/auswählen oder 2) direkt einen neuen erstellen können, ohne in die
// Administration zu wechseln. Backend erstellt einen unbekannten Tag-Namen beim Speichern
// automatisch (entity_links.sync_tags) - hier geht es nur um die Klarheit der UX: existierende
// Treffer vs. "existiert nicht -> erstellen" sind sichtbar unterschieden (statt einer
// einzelnen Freitext-Eingabe ohne Rückmeldung).
export default function TagInput({ value, onChange }: { value: string[]; onChange: (tags: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [searchedTerm, setSearchedTerm] = useState<string | null>(null);

  useEffect(() => {
    if (!draft.trim()) {
      setSuggestions([]);
      setSearchedTerm(null);
      return;
    }
    const handle = setTimeout(() => {
      const term = draft.trim();
      api
        .listTags(term)
        .then((tags) => {
          setSuggestions(tags.map((t) => t.name).filter((name) => !value.includes(name)));
          setSearchedTerm(term);
        })
        .catch(() => setSuggestions([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [draft, value]);

  const trimmedDraft = draft.trim();
  const exactMatch = suggestions.some((s) => s.toLowerCase() === trimmedDraft.toLowerCase());
  const alreadyChosen = value.some((v) => v.toLowerCase() === trimmedDraft.toLowerCase());
  const showCreateHint = trimmedDraft.length > 0 && searchedTerm === trimmedDraft && !exactMatch && !alreadyChosen;

  const addTag = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed || value.includes(trimmed)) return;
    onChange([...value, trimmed]);
    setDraft("");
    setSuggestions([]);
    setSearchedTerm(null);
  };

  const removeTag = (name: string) => onChange(value.filter((t) => t !== name));

  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginBottom: value.length > 0 ? "0.4rem" : 0 }}>
        {value.map((tag) => (
          <span key={tag} className="legend-chip" style={{ background: "#eef3fa", padding: "0.1rem 0.5rem", borderRadius: "999px" }}>
            #{tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer", marginLeft: "0.25rem" }}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            addTag(draft);
          }
        }}
        placeholder="Tag hinzufügen (Enter) …"
        style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", fontSize: "0.85rem" }}
      />
      {suggestions.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.35rem" }}>
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              className="btn secondary"
              style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
              onClick={() => addTag(s)}
            >
              #{s}
            </button>
          ))}
        </div>
      )}
      {showCreateHint && (
        <div style={{ marginTop: "0.35rem", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ color: "var(--text-muted)" }}>„{trimmedDraft}“ existiert nicht</span>
          <button
            type="button"
            className="btn secondary"
            style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
            onClick={() => addTag(trimmedDraft)}
          >
            + #{trimmedDraft} erstellen
          </button>
        </div>
      )}
    </div>
  );
}
