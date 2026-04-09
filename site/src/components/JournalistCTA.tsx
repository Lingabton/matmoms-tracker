import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function JournalistCTA({ data }: Props) {
  const shareText = "Var är maten billigast — ICA, Coop eller Willys? Daglig prisjämförelse på matmoms.se";
  const shareUrl = "https://matmoms.se";

  return (
    <>
      <div className="share-bar" id="data">
        <span>Dela</span>
        <a href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`} target="_blank" rel="noopener noreferrer">X / Twitter</a>
        <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`} target="_blank" rel="noopener noreferrer">Facebook</a>
        <a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`} target="_blank" rel="noopener noreferrer">LinkedIn</a>
      </div>

      <div className="cta-section">
        <div className="cta-inner">
          <div>
            <h3>Journalist eller forskare?</h3>
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
            <div className="cta-feature"><div className="dot" />Dagliga observationer från baslinje till idag</div>
            <div className="cta-feature"><div className="dot" />CSV, JSON, API</div>
            <div className="cta-feature"><div className="dot" />Kampanjpriser separerade från ordinarie</div>
            <div className="cta-feature"><div className="dot" />Uppdatering dagligen kl. 06:00</div>
          </div>
        </div>
      </div>
    </>
  );
}
