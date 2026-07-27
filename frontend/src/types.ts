export type PhaseCode = "p" | "k" | "t" | "g" | "?";

export const PHASE_LABELS: Record<PhaseCode, string> = {
  p: "Pflichtenheft",
  k: "Konfiguration",
  t: "Test",
  g: "GoLive",
  "?": "Meilenstein",
};

export const PHASE_COLORS: Record<PhaseCode, string> = {
  p: "#0A55B9",
  k: "#288CE1",
  t: "#C355D7",
  g: "#CD145A",
  "?": "#002F5E",
};

export interface ProjectSummary {
  id: number;
  name: string;
  kunde: string | null;
  start_monat: string;
  anzahl_monate: number;
  monate: string[];
}

export interface SubprojectDetail {
  id: number;
  name: string;
  reihenfolge: number;
  phasen: Record<string, PhaseCode[]>;
  fte: Record<string, number>;
}

export interface ProjectDetail extends ProjectSummary {
  subprojects: SubprojectDetail[];
}
