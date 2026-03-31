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
            Trippelkontroll på matchning: storlek (±15%), varumärke och variant
            (eko/laktosfri) måste stämma.
          </p>
        </div>
        <div className="method-item">
          <h4>Baslinje</h4>
          <p>
            Medianpriset per produkt och butik under 30–31 mars 2026.
            Kampanjpriser exkluderas. Se not om tidiga sänkningar nedan.
          </p>
        </div>
        <div className="method-item">
          <h4>Genomslagsberäkning</h4>
          <p>
            Faktisk prissänkning dividerat med den förväntade sänkningen
            på 5,36%. 100% = hela momssänkningen nådde konsumenten.
          </p>
        </div>
        <div className="method-item">
          <h4>Begränsningar</h4>
          <p>
            Kedjornas sökmotorer returnerar inte alltid rätt produkt.
            Strikt matchning minimerar felkällor men sänker träffsäkerheten.
            Baslinjen är 2 dagar (idealt 7).
          </p>
        </div>

        <div className="formula-block">
{`genomslag = (baslinjepris − nytt pris) / (baslinjepris × 0.0536)

där 0.0536 = 1 − 1.06/1.12 = förväntad prissänkning vid full genomslagskraft`}
        </div>
      </div>

      <div className="method-note">
        <h4>Observation: Tidiga prissänkningar</h4>
        <p>
          Trots att momssänkningen träder i kraft 1 april har vi observerat
          att ett antal ICA-butiker sänkte priser redan 30 mars. I vår data
          sjönk 19% av ICA:s priser med mer än 3% mellan 30 och 31 mars,
          medan Willys hade 0% sänkningar under samma period.
        </p>
        <p>
          Detta innebär att vår baslinje för ICA delvis kan inkludera
          redan sänkta priser, vilket <strong>underskattar</strong> ICA:s
          faktiska genomslag. Vi redovisar detta transparent och
          rekommenderar att ICA:s siffror tolkas som en nedre gräns.
        </p>
      </div>
    </div>
  );
}
