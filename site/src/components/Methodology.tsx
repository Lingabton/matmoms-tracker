export function Methodology() {
  return (
    <div className="card" id="metod">
      <h2>Metod</h2>
      <div style={{ fontSize: "0.9rem", lineHeight: 1.8 }}>
        <p>
          <strong>Datainsamling:</strong> Priser samlas in dagligen fran ICA,
          Coop och Willys webbplatser med automatiserade skrapare. Vi overvakar
          419 livsmedel i 33 butiker over 9 stader.
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Baslinje:</strong> Medianpriset per produkt och butik under
          perioden fore 1 april 2026 (exklusive kampanjpriser).
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Genomslag:</strong> For varje produkt-butik-kombination
          beraknar vi:
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

dar 0.0536 = 1 - 1.06/1.12
           = forvantad prissankning`}
        </pre>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Kampanjfilter:</strong> Observationer flaggade som kampanj,
          erbjudande eller medlemspris exkluderas fran baslinjen for att undvika
          att tillfalliga prissakningar snedvrider resultatet.
        </p>
        <p style={{ marginTop: "0.75rem" }}>
          <strong>Begransningar:</strong> Sokmotorerna pa kedjornas webbplatser
          returnerar inte alltid exakt ratt produkt. Vi anvander automatisk
          matchning pa varumarke, forpackningsstorlek och produktnamn for att
          minimera felkallor.
        </p>
      </div>
    </div>
  );
}
