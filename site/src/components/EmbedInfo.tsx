import { useState } from "react";

export function EmbedInfo() {
  const [copied, setCopied] = useState(false);
  const embedCode = `<iframe src="https://matmoms.se/embed.html" width="480" height="340" frameborder="0" style="border:1px solid #e8e6e1;border-radius:8px;max-width:100%"></iframe>`;

  const copy = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="section-block reveal" id="embed">
      <div className="section-header">
        <h2>Bädda in på din sajt</h2>
        <p>
          Gratis widget med live-data. Uppdateras automatiskt dagligen.
          Perfekt för nyhetsredaktioner, bloggar och kommuner.
        </p>
      </div>
      <div className="embed-preview">
        <iframe
          src="/embed.html"
          width="480"
          height="340"
          frameBorder="0"
          style={{ border: "1px solid #e8e6e1", borderRadius: "8px", maxWidth: "100%" }}
          title="Matmoms widget"
        />
      </div>
      <div className="embed-code">
        <code>{embedCode}</code>
        <button onClick={copy} className="copy-btn">
          {copied ? "Kopierat!" : "Kopiera kod"}
        </button>
      </div>
    </div>
  );
}
