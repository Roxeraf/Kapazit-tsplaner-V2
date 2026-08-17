import { useEffect, useState } from "react";
import { api } from "../api/client";

// Phase 26.1: Owner-/Zuständig-/Entschieden-von-Felder sind jetzt Person-FKs statt Freitext
// (siehe RiskList/TaskList/DecisionList) - für die Anzeige des Namens reicht eine einmalig
// geladene id -> display_name-Map, kein serverseitiger Join nötig (BlockerOut macht das
// ebenso, siehe backend/app/schemas.py).
export default function usePeopleMap(): Map<number, string> {
  const [map, setMap] = useState<Map<number, string>>(new Map());

  useEffect(() => {
    api
      .listPeople()
      .then((people) => setMap(new Map(people.map((p) => [p.id, p.display_name]))))
      .catch(() => setMap(new Map()));
  }, []);

  return map;
}
