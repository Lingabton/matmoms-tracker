import { useState } from "react";

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="site-nav">
      <div className="inner">
        <a href="#" className="logo">
          mat<span>moms</span>
        </a>
        <button
          className="nav-toggle"
          onClick={() => setOpen(!open)}
          aria-label="Meny"
          aria-expanded={open}
        >
          <span />
          <span />
          <span />
        </button>
        <div className={`links ${open ? "open" : ""}`}>
          <a href="#priser" onClick={() => setOpen(false)}>Priser</a>
          <a href="#kedja" onClick={() => setOpen(false)}>Kedjor</a>
          <a href="#kategori" onClick={() => setOpen(false)}>Kategorier</a>
          <a href="#embed" onClick={() => setOpen(false)}>Embed</a>
          <a href="#data" onClick={() => setOpen(false)}>Data</a>
          <a href="#metod" onClick={() => setOpen(false)}>Metod</a>
        </div>
      </div>
    </nav>
  );
}
