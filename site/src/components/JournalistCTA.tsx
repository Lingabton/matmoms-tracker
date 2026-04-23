import { useState } from "react";
import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function JournalistCTA({ data }: Props) {
  const [copied, setCopied] = useState(false);
  const embedCode = `<iframe src="https://matmoms.se/embed.html" width="480" height="340" frameborder="0" style="border:1px solid #e8e6e1;border-radius:8px;max-width:100%"></iframe>`;

  const copy = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="cta-section" id="data">
      <div className="cta-inner">
        <div>
          <h3>Journalist, forskare eller bloggare?</h3>
          <p>
            Fullständig produktdata med {data.summary.totalProducts} varor
            och {data.summary.totalStores} butiker. Dagliga prisobservationer
            med verifierad produktmatchning.
          </p>
          <a className="cta-btn" href="mailto:gabriel.linton@gmail.com?subject=Matmoms%20-%20datatillg%C3%A5ng">
            Kontakta oss
          </a>
        </div>
        <div className="cta-features">
          <div className="cta-feature"><div className="dot" />{data.summary.totalProducts} varor med pris, varumärke, kategori</div>
          <div className="cta-feature"><div className="dot" />{data.summary.totalStores} butiker i {data.byCity?.length ?? 0} städer</div>
          <div className="cta-feature"><div className="dot" />CSV, JSON, API</div>
          <div className="cta-feature"><div className="dot" />Kampanjpriser separerade från ordinarie</div>
          <div className="cta-feature"><div className="dot" />Uppdatering dagligen kl. 06:00</div>
        </div>
      </div>
      <div className="cta-embed">
        <div className="cta-embed-label">Bädda in widget</div>
        <div className="embed-code" style={{ maxWidth: "var(--max-w)", margin: "0 auto" }}>
          <code>{embedCode}</code>
          <button onClick={copy} className="copy-btn">
            {copied ? "Kopierat!" : "Kopiera"}
          </button>
        </div>
      </div>
    </div>
  );
}
