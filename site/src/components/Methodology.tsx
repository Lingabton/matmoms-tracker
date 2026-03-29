export function Methodology() {
  return (
    <div className="section-block reveal" id="metod">
      <div className="section-header">
        <h2>Metod</h2>
        <p>Transparent datainsamling och beräkning</p>
      </div>

      <div className="method-grid">
        <div className="method-item">
          <h4>Datainsamling</h4>
          <p>
            Priser samlas in dagligen från ICA, Coop och Willys via deras
            produkt-API:er. 419 livsmedel i 33 butiker över 9 städer.
          </p>
        </div>
        <div className="method-item">
          <h4>Produktmatchning</h4>
          <p>
            Trippelkontroll: storlek (±15%), varumärke och variant
            (eko/laktosfri) måste stämma. Hellre "ej hittad" än felmatchning.
          </p>
        </div>
        <div className="method-item">
          <h4>Baslinje</h4>
          <p>
            Medianpriset per produkt och butik före 1 april 2026.
            Kampanjpriser exkluderas.
          </p>
        </div>
        <div className="method-item">
          <h4>Begränsningar</h4>
          <p>
            Kedjornas sökmotorer returnerar inte alltid rätt produkt.
            Strikt matchning minimerar felkällor men sänker träffsäkerheten.
          </p>
        </div>

        <div className="formula-block">
{`genomslag = (baslinjepris − nytt pris) / (baslinjepris × 0.0536)

där 0.0536 = 1 − 1.06/1.12 = förväntad prissänkning vid full genomslagskraft`}
        </div>
      </div>
    </div>
  );
}
