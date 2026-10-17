import { useEffect } from "react";

import { loadMAT1Catalog } from "../api/mat1Service";
import { setMAT1Active, setMAT1Catalog, setMAT1CatalogError } from "../state/mat1Session";
import { App } from "./App";

export function MAT1ProductBootstrap() {
  useEffect(() => {
    const controller = new AbortController();
    setMAT1Active(true);
    void loadMAT1Catalog(controller.signal)
      .then((records) => { if (!controller.signal.aborted) setMAT1Catalog(records); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setMAT1CatalogError(error instanceof Error ? error.message : "Material catalog unavailable.");
      });
    return () => { controller.abort(); setMAT1Active(false); };
  }, []);
  return <App />;
}
