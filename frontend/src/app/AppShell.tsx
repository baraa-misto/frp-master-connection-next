import { useState } from "react";

import type { PrimaryCategoryId } from "../domain/designCategories";
import { CategorySelector } from "../features/CategorySelector";
import { ConnectorMaterialReadiness } from "../features/ConnectorMaterialReadiness";
import { WorkspacePreview } from "../views/WorkspacePreview";

export function AppShell() {
  const [selectedCategory, setSelectedCategory] = useState<PrimaryCategoryId | null>(null);

  return (
    <div className="application-frame">
      <header className="product-header">
        <div>
          <p className="product-kicker">Masters Engineering Solutions</p>
          <h1>FRP Master Connection</h1>
        </div>
        <p className="stage-badge">Engineering design workspace</p>
      </header>

      <aside className="safety-notice" aria-labelledby="safety-title">
        <div className="safety-marker" aria-hidden="true">!</div>
        <div>
          <h2 id="safety-title">Design completeness</h2>
          <p>
            Each workspace identifies the checks it can execute and the evidence still needed for
            a complete design. Reports are available for evaluated and partial designs; the result
            keeps source, qualification, geometry, and unsupported-method limits visible.
          </p>
        </div>
      </aside>

      <main className="application-main">
        <section className="selection-panel" aria-labelledby="category-title">
          <div className="section-heading">
            <p className="section-number">01</p>
            <div>
              <h2 id="category-title">Choose a primary design category</h2>
              <p>Select a connection family to start a design.</p>
            </div>
          </div>
          <CategorySelector selectedCategory={selectedCategory} onSelect={setSelectedCategory} />
        </section>

        <WorkspacePreview selectedCategory={selectedCategory} />
        {selectedCategory === "shear" ? null : <ConnectorMaterialReadiness />}
      </main>

      <footer className="product-footer">
        <p>Three.js / React Three Fiber presentation · canonical backend snapshot</p>
        <p>Frontend client is untrusted, non-authoritative, and session-only.</p>
      </footer>
    </div>
  );
}
