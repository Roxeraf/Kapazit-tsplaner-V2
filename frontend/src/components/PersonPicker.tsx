import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { AdminPerson } from "../types";

// Phase 26.1: ersetzt die bisherigen Freitext-Zuordnungsfelder (Projektleiter/Owner) durch
// einen wiederverwendbaren Personen-Picker gegen das Personenverzeichnis (Person, Phase 14).
// Muster von TagInput.tsx übernommen (Suchfeld + Vorschlagsliste), hier aber Single-Select
// mit fest gewählter Person statt Mehrfach-Tags.
export default function PersonPicker({
  value,
  onChange,
  onPersonChange,
  placeholder = "Person suchen …",
}: {
  value: number | null;
  onChange: (personId: number | null) => void;
  /** Optional: liefert zusätzlich das volle Person-Objekt (z.B. für display_name-Anzeige an anderer Stelle). */
  onPersonChange?: (person: AdminPerson | null) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<AdminPerson[]>([]);
  const [selected, setSelected] = useState<AdminPerson | null>(null);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value == null) {
      setSelected(null);
      return;
    }
    if (selected?.id === value) return;
    api
      .listPeople()
      .then((people) => setSelected(people.find((p) => p.id === value) ?? null))
      .catch(() => setSelected(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => {
      api
        .listPeople(query.trim() || undefined)
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [query, open]);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const pick = (person: AdminPerson) => {
    setSelected(person);
    onChange(person.id);
    onPersonChange?.(person);
    setQuery("");
    setOpen(false);
  };

  const clear = () => {
    setSelected(null);
    onChange(null);
    onPersonChange?.(null);
    setQuery("");
  };

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      {selected ? (
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span className="legend-chip" style={{ background: "#eef3fa", padding: "0.15rem 0.6rem", borderRadius: "999px" }}>
            {selected.display_name}
          </span>
          <button
            type="button"
            onClick={clear}
            className="btn secondary"
            style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
          >
            Ändern
          </button>
        </div>
      ) : (
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", fontSize: "0.85rem", width: "100%" }}
        />
      )}
      {open && !selected && suggestions.length > 0 && (
        <div
          style={{
            position: "absolute",
            zIndex: 10,
            marginTop: "0.2rem",
            background: "#fff",
            border: "1px solid var(--border)",
            borderRadius: "4px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            minWidth: "100%",
            maxHeight: "220px",
            overflowY: "auto",
          }}
        >
          {suggestions.map((p) => (
            <button
              type="button"
              key={p.id}
              onClick={() => pick(p)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "0.35rem 0.6rem",
                border: "none",
                background: "none",
                cursor: "pointer",
                fontSize: "0.85rem",
              }}
            >
              {p.display_name}
              {p.email && <span style={{ color: "var(--text-muted)", marginLeft: "0.4rem" }}>{p.email}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
