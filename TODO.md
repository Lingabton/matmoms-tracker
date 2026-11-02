# Matmoms — Roadmap

## Klart
- [x] Månatlig CSV-snapshot på GitHub Releases (CC BY 4.0)
- [x] Data-sektion på sajten med nedladdning + mailgate för full historik
- [x] Fixat 3 trasiga ICA-butiker (Göteborg, Torslanda, Malmö)
- [x] Förbättrad matchningslogik (brand-normalisering, flexibel storlek, färre falska positiva)
- [x] EMV-filtrering (Garant bara på Willys, Coop-märken bara på Coop, etc.)

## Nästa steg

### 1. SCB KPI-validering
Koppla Matmoms-data till SCB:s officiella KPI-livsmedelsserie. Visa hur väl
dagligvarupriserna i vårt dataset spårar SCB:s månadsindex. Ger trovärdighet
och en unik vinkel: daglig upplösning vs SCB:s månadsdata.

### 2. Matmoms Basket Index
Veckoprisindex per kedja för en standardkorg (~30 basvaror). Visar vilken
kedja som är billigast och hur det förändras över tid. Bra visualisering
för sajten och journalister.

### 3. Utöka produktkatalogen
Lägg till fler basvaror med fokus på SCB:s KPI-korg. Varje produkt behöver
EAN, söktermer per kedja, och validering mot scrapers. Mål: 800+ produkter.

### 4. Kampanjanalys
Analysera kampanjdata: hur ofta är kampanjpris lägre än konkurrentens
ordinarie pris? Hur långa är "tillfälliga" kampanjer egentligen? Mediavänliga
insikter.

### 5. Forskarexport (Parquet + dokumentation)
Exportera till Parquet-format med kodbok och dataspecifikation. Gör datan
enkel att ladda i Python/R för akademisk forskning.
