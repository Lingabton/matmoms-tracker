import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function DataDownload({ data }: Props) {
  const releaseUrl =
    "https://github.com/Lingabton/matmoms-tracker/releases/latest";

  return (
    <div className="section" id="data">
      <div className="data-download reveal">
        <div className="data-header">
          <h2>Öppen data</h2>
          <p>
            Daglig prisdata från {data.summary.totalStores} butiker och{" "}
            {data.summary.totalProducts} produkter — fritt att använda med
            attribution.
          </p>
        </div>

        <div className="data-grid">
          <div className="data-card">
            <div className="data-card-label">Gratis snapshot</div>
            <h3>Senaste månaden</h3>
            <p>
              Fullständiga prisobservationer, produktkatalog och butikslista i
              CSV-format. Uppdateras automatiskt den 1:a varje månad.
            </p>
            <a className="data-btn" href={releaseUrl}>
              Ladda ner CSV
            </a>
            <span className="data-license">CC BY 4.0 — citera matmoms.se</span>
          </div>

          <div className="data-card data-card--full">
            <div className="data-card-label">Full historik</div>
            <h3>Mars 2026 → idag</h3>
            <p>
              580 000+ prisobservationer med daglig upplösning. Perfekt för
              tidsserieanalys, ML-projekt, forskning eller journalistik.
            </p>
            <a
              className="data-btn data-btn--outline"
              href="mailto:gabriellinton@gmail.com?subject=Matmoms%20-%20full%20historik"
            >
              Maila för tillgång
            </a>
            <span className="data-license">
              Beskriv kort vad du ska använda datan till
            </span>
          </div>
        </div>

        <div className="data-attribution">
          <strong>Attribution (obligatorisk):</strong> Källa: Matmoms
          (matmoms.se) av Gabriel Linton
        </div>
      </div>
    </div>
  );
}
