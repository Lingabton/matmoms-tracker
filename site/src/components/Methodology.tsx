export function Methodology() {
  return (
    <div className="section-block reveal" id="metod">
      <div className="section-header">
        <h2>Metod</h2>
        <p>Transparent datainsamling och kvalitetskontroll</p>
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
          <h4>Kvalitetskontroll</h4>
          <p>
            Automatisk outlier-detektion flaggar priser som avviker mer än
            80% från produktmedianen. Prisexempel kräver verifierad matchning
            från alla tre kedjor med max 60% prisspridning.
          </p>
        </div>
        <div className="method-item">
          <h4>Prishistorik</h4>
          <p>
            Vi sparar dagliga priser per produkt och kedja sedan mars 2026.
            Prishistoriken visar trender och säsongsvariationer.
            Data inkluderar uppföljning av momssänkningen (12% &rarr; 6%, 1 april 2026).
          </p>
        </div>
        <div className="method-item">
          <h4>Begränsningar</h4>
          <p>
            Kedjornas sökmotorer returnerar inte alltid rätt produkt.
            Strikt matchning minimerar felkällor men sänker träffsäkerheten.
            Coop-matchning har kända problem med liknande produktnamn.
          </p>
        </div>

        <div className="formula-block">
{`Prisjustering (genomslag av momssänkning):
genomslag = (baslinjepris − nytt pris) / (baslinjepris × 0.0536)
där 0.0536 = 1 − 1.06/1.12 = förväntad prissänkning`}
        </div>
      </div>
    </div>
  );
}
