import type { PropsWithChildren } from "react";

import "./Card.css";

/**
 * Generischer, "dummer" UI-Baustein (kein Feature-Wissen).
 * Entspricht optisch der alten .card-Klasse aus utilities.css.
 */
export function Card({ children }: PropsWithChildren) {
  return <div className="card">{children}</div>;
}
