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
        <p className="stage-badge">Stage 2.6B · Eccentric group-mode integration</p>
      </header>

      <aside className="safety-notice" aria-labelledby="safety-title">
        <div className="safety-marker" aria-hidden="true">!</div>
        <div>
          <h2 id="safety-title">Engineering scope boundary</h2>
          <p>
            This development workspace exposes the verified single-bolt slice and the controlled
            rectangular multi-row workflow. It is not a complete connection design, qualification,
            or report. Server-returned review, source-pending, unsupported, and Section 2.3.2
            statuses remain mandatory engineering limits.
          </p>
        </div>
      </aside>

      <main className="application-main">
        <section className="selection-panel" aria-labelledby="category-title">
          <div className="section-heading">
            <p className="section-number">01</p>
            <div>
              <h2 id="category-title">Choose a primary design category</h2>
              <p>Select the implemented Shear workspace or inspect the deferred Moment scope.</p>
            </div>
          </div>
          <CategorySelector selectedCategory={selectedCategory} onSelect={setSelectedCategory} />
        </section>

        <WorkspacePreview selectedCategory={selectedCategory} />
        <ConnectorMaterialReadiness />
      </main>

      <footer className="product-footer">
        <p>Three.js / React Three Fiber presentation · canonical backend snapshot</p>
        <p>Frontend client is untrusted, non-authoritative, and session-only.</p>
      </footer>
    </div>
  );
}
