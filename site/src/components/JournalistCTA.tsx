import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function JournalistCTA({ data }: Props) {
  const shareText = "Matmomsen sänks från 12% till 6%. Blev maten billigare? Kolla matmoms.se";
  const shareUrl = "https://matmoms.se";

  return (
    <div id="data">
      {/* Social sharing */}
      <div className="share-bar">
        <span>Dela:</span>
        <a
          href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          X / Twitter
        </a>
        <a
          href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Facebook
        </a>
        <a
          href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          LinkedIn
        </a>
      </div>

      <div className="cta-box">
        <h3>Journalist eller forskare?</h3>
        <p>
          Vi erbjuder fullständig produktdata med{" "}
          {data.summary.totalProducts} varor, {data.summary.totalStores} butiker
          och dagliga prisobservationer. Perfekt för redaktioner och forskare som
          vill analysera momssänkningens effekt.
        </p>
        <a className="btn" href="mailto:gabriel.linton@gmail.com?subject=Matmoms%20-%20datatillg%C3%A5ng">
          Kontakta oss för datatillgång
        </a>
      </div>

      <div className="card">
        <h2>Vad ingår i datasetet?</h2>
        <table className="data-table">
          <tbody>
            <tr>
              <td>Produktnivå</td>
              <td>{data.summary.totalProducts} varor med pris, varumärke, kategori</td>
            </tr>
            <tr>
              <td>Butiksnivå</td>
              <td>{data.summary.totalStores} butiker i {data.byCity?.length ?? 0} städer</td>
            </tr>
            <tr>
              <td>Historik</td>
              <td>Dagliga observationer från baslinje till idag</td>
            </tr>
            <tr>
              <td>Format</td>
              <td>CSV, JSON, API</td>
            </tr>
            <tr>
              <td>Kampanjfilter</td>
              <td>Flaggade kampanjpriser separerade från ordinarie</td>
            </tr>
            <tr>
              <td>Uppdatering</td>
              <td>Dagligen kl. 06:00</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
