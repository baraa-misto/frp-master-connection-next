import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";

import { App } from "./App";

export function mountApplication(container: HTMLElement | null): Root {
  if (container === null) {
    throw new Error("FRP Master Connection application root was not found.");
  }

  const root = createRoot(container);
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
  return root;
}
