import { useEffect, useRef, useState } from "react";

/**
 * Cycles through a list of labels describing the real stages a request is
 * moving through server-side (Supervisor decision -> tool calls -> Reflection
 * check), while that request has no per-stage signal of its own to report
 * (session/start isn't an SSE route - see agents/graph.py's turn shape in
 * master_plan.md). Not a fake progress bar: each label names an actual
 * pipeline step, just without knowing exactly when each one finishes.
 */
export function useStagedLoadingLabel(stages: readonly string[], active: boolean, stepMs = 1400): string {
  const [index, setIndex] = useState(0);
  const stagesRef = useRef(stages);
  stagesRef.current = stages;

  useEffect(() => {
    if (!active) {
      setIndex(0);
      return;
    }
    const id = window.setInterval(() => {
      setIndex((current) => Math.min(current + 1, stagesRef.current.length - 1));
    }, stepMs);
    return () => window.clearInterval(id);
  }, [active, stepMs]);

  return stages[index] ?? stages[0];
}
