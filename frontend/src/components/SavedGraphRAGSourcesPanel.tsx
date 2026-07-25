import { useState } from "react";
import { ChevronDown, ExternalLink, Network } from "lucide-react";

import { type GraphRAGProvenance } from "../api/assistant";

type SavedGraphRAGSourcesPanelProps = {
  provenance: GraphRAGProvenance;
};

export function SavedGraphRAGSourcesPanel({ provenance }: SavedGraphRAGSourcesPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const sourceCount = provenance.sources.length;

  return (
    <section className={"reasoning-panel saved-graphrag-sources-panel " + (isOpen ? "is-open" : "is-preview")} aria-label="GraphRAG források">
      <button className="reasoning-panel__header" type="button" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen}>
        <span className="reasoning-panel__status">
          <span className="saved-graphrag-sources-panel__icon" aria-hidden="true">
            <Network size={15} />
          </span>
          Források
          <span className="saved-graphrag-sources-panel__count">{sourceCount}</span>
        </span>
        <span className="reasoning-panel__toggle">
          {isOpen ? "Bezárás" : "Megnyitás"}
          <ChevronDown size={15} aria-hidden="true" />
        </span>
      </button>
      {isOpen ? (
        <div className="reasoning-panel__body">
          <div className="saved-graphrag-sources-panel__meta">
            <span>Típus: {provenance.query_type}</span>
            {provenance.truncated ? <span className="saved-graphrag-sources-panel__warning">Rövidített retrieval</span> : null}
          </div>
          {sourceCount > 0 ? (
            <ol className="saved-graphrag-sources-panel__list">
              {provenance.sources.map((source, index) => {
                const heading = source.heading_path.join(" › ");
                const obsidianUri = safeObsidianUri(source.obsidian_uri);
                return (
                  <li key={source.source_id}>
                    <div className="saved-graphrag-sources-panel__source-title">
                      <span>[S{index + 1}] {source.relative_path}</span>
                      {obsidianUri ? (
                        <a href={obsidianUri} aria-label={"Forrás megnyitása Obsidianban: " + source.relative_path} title="Megnyitás Obsidianban">
                          <ExternalLink size={14} aria-hidden="true" />
                        </a>
                      ) : null}
                    </div>
                    {heading ? <div className="saved-graphrag-sources-panel__heading">{heading}</div> : null}
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="saved-graphrag-sources-panel__empty">A retrieval nem adott vissza felhasználható forrást.</p>
          )}
          {provenance.warnings.length > 0 ? (
            <ul className="saved-graphrag-sources-panel__warnings">
              {provenance.warnings.map((warning) => (
                <li key={warning.code + warning.message}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function safeObsidianUri(value: string | null): string | null {
  if (!value || !value.toLowerCase().startsWith("obsidian://")) {
    return null;
  }
  return value;
}
