# VoH — Dashboard Standalone (single-file HTML)

Versione **autosufficiente** della dashboard VoH: tutto in un singolo file
`dashboard.html`. Nessun backend, nessuna build, nessun npm.

Ideale per:
- demo veloci
- caricamento su un server HTTP statico (Apache, nginx, GitHub Pages, ...)
- presentazioni offline (basta aprirla con doppio click)

## Cosa contiene

- Generatore di telemetrie simulate per i 4 ambienti VoH (in-browser, AR(1))
- 8 manoscritti precaricati con caratterizzazione codicologica
- Le 5 formule di rischio Michalski–Verticchio (f(pH), Brimblecombe, Sedlbauer, EN 15757, ΔE*)
- Matrice pesi ambiente-dipendente (D4.2.2.2 Tab. 3)
- Le 7 viste della dashboard: Collezione, Ambiente, Manufatto, Predittiva, Alert, Demo, Linee Guida
- Pannello Demo Scenarios A–E
- Motore alert + raccomandazioni a 3 sezioni

## Differenze rispetto alla versione full-stack

| Aspetto | Full-stack | Standalone |
|---|---|---|
| Backend | FastAPI + Python | nessuno (tutto JS) |
| DBSCAN/GBR reali | sì (scikit-learn) | sostituiti con label_from_RI + regressione lineare |
| Storico iniziale | 90 giorni | 30 giorni |
| Persistenza | CSV + .pkl | nessuna (volatile) |
| WebSocket live | sì | setInterval 1s in-browser |

## Come usarlo

### Apertura locale
Doppio click su `dashboard.html` (alcuni browser potrebbero richiedere di
servirlo via HTTP, vedi sotto).

### Server HTTP statico

```bash
# Python
python -m http.server 8080
# poi apri http://localhost:8080/dashboard.html

# o Node
npx serve .

# o nginx, Apache, ecc. — basta copiare dashboard.html nella docroot
```

### GitHub Pages / Vercel / Netlify
Carica il singolo `dashboard.html` come pagina statica.

## Dipendenze esterne (caricate da CDN)

- React 18 (UMD)
- ReactDOM 18 (UMD)
- Recharts 2.13 (UMD)
- Tailwind CSS Play CDN
- Babel Standalone (per il JSX inline)

Richiede connessione a Internet la prima volta. Per uso completamente offline,
scarica i bundle dai CDN e referenziali localmente.

---

*Sistema VoH — CeRICT — Architettura predittiva derivata da EFAISTOS
(Test Before Invest, Polo P.R.I.D.E.). Sensore artunified multiparametrico.*
