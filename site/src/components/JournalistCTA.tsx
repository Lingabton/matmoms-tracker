import type { SiteData } from "../hooks/useData";

interface Props {
  data: SiteData;
}

export function JournalistCTA({ data }: Props) {
  return (
    <div id="data">
      <div className="cta-box">
        <h3>Datajournalist?</h3>
        <p>
          Vi erbjuder fullstandig produktdata med{" "}
          {data.summary.totalProducts} varor, {data.summary.totalStores} butiker
          och dagliga prisobservationer. Perfekt for redaktioner som vill grava i
          momssankningen.
        </p>
        <a className="btn" href="mailto:gabriel.linton@gmail.com?subject=Matmoms%20data">
          Kontakta oss for datatillgang
        </a>
      </div>

      <div className="card">
        <h2>Vad ingar?</h2>
        <table className="data-table">
          <tbody>
            <tr>
              <td>Produktniva-data</td>
              <td>{data.summary.totalProducts} varor med pris, varumarke, kategori</td>
            </tr>
            <tr>
              <td>Butiksniva</td>
              <td>{data.summary.totalStores} butiker i {data.byCity?.length ?? 0} stader</td>
            </tr>
            <tr>
              <td>Historik</td>
              <td>Dagliga observationer fran baslinje till idag</td>
            </tr>
            <tr>
              <td>Format</td>
              <td>CSV, JSON, API</td>
            </tr>
            <tr>
              <td>Kampanjfilter</td>
              <td>Flaggade kampanjpriser separerade fran ordinarie</td>
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
