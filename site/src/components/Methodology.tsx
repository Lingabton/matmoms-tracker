export function Methodology() {
  return (
    <div className="card" id="metod">
      <h2>Metod</h2>
      <div style={{ fontSize: "0.9rem", lineHeight: 1.8 }}>
        <p>
          <strong>Datainsamling:</strong> Priser samlas in dagligen från ICA,
          Coop och Willys webbplatser med automatiserade skrapare. Vi övervakar
          419 livsmedel i 33 butiker över 9 städer.
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Baslinje:</strong> Medianpriset per produkt och butik under
          perioden före 1 april 2026 (exklusive kampanjpriser).
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Genomslag:</strong> För varje produkt-butik-kombination
          beräknar vi:
        </p>
        <pre
          style={{
            background: "var(--color-bg)",
            padding: "0.75rem",
            borderRadius: "6px",
            margin: "0.5rem 0",
            fontSize: "0.8rem",
            fontFamily: "var(--font-mono)",
            overflow: "auto",
          }}
        >
{`genomslag = (baslinjepris - nytt pris)
           / (baslinjepris x 0.0536)

där 0.0536 = 1 - 1.06/1.12
           = förväntad prissänkning`}
        </pre>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Kampanjfilter:</strong> Observationer flaggade som kampanj,
          erbjudande eller medlemspris exkluderas från baslinjen för att undvika
          att tillfälliga prissänkningar snedvrider resultatet.
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Begränsningar:</strong> Sökmotorerna på kedjornas webbplatser
          returnerar inte alltid exakt rätt produkt. Vi använder automatisk
          matchning på varumärke, förpackningsstorlek och produktnamn för att
          minimera felkällor.
        </p>
      </div>
    </div>
  );
}
