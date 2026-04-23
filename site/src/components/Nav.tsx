import { useState } from "react";

interface Props {
  basketCount: number;
}

export function Nav({ basketCount }: Props) {
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
          <a href="#sok" onClick={() => setOpen(false)}>Sök</a>
          <a href="#varukorg" onClick={() => setOpen(false)} className="nav-basket">
            Varukorg{basketCount > 0 && <span className="nav-badge">{basketCount}</span>}
          </a>
          <a href="#kedja" onClick={() => setOpen(false)}>Kedjor</a>
          <a href="#kategori" onClick={() => setOpen(false)}>Kategorier</a>
          <a href="#metod" onClick={() => setOpen(false)}>Metod</a>
        </div>
      </div>
    </nav>
  );
}
