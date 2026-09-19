# DomainMate — Piano Quick Wins ad Alto ROI

> Analisi del 19 settembre 2026 su `main` (commit `cc8adcd`, 47 commit, 2.082 righe Python).
> Ogni punto è stato verificato eseguendo il codice, non solo leggendolo.

---

## 0. Stato

**Lotto 0 completato** (#1, #2, #6, #7). Il resto del piano è invariato.

| # | Quick win | Stato |
|---|---|---|
| 1 | Exit code per la CI | ✅ `--fail-on` + `--json`, 21 test nuovi |
| 2 | Pinning dipendenze | ✅ 14 pin `==` + Dependabot (pip, actions, npm) |
| 6 | Docker non-root | ✅ UID/GID 10001 + `.dockerignore` (46 → 17 file nel contesto) |
| 7 | encoding esplicito | ✅ 6 `open()` + `ensure_ascii=False` sui dump JSON |

Due note sul Lotto 0:

- Il contenitore ora gira come UID 10001, quindi una `reports/` montata da host
  va resa scrivibile: `sudo chown -R 10001:10001 reports`.
- `config.yaml` non finisce più nell'immagine (contiene la lista domini, che
  verrebbe distribuita a ogni pull). Va montato a runtime — `docker-compose.yml`
  e `make docker-run` lo fanno già.

---

## 1. Lo scope, in breve

| Dimensione | Stato |
|---|---|
| Codice | ~2.100 righe Python (5 monitor, CLI, API FastAPI, generatore HTML, 6 canali di notifica) |
| Superfici | CLI `src/cli.py` · API `api/api.py` · report HTML statico · immagine Docker |
| Test | 35 test, tutti verdi, nessuna rete (`pytest -q` → 0,74 s) |
| CI | test → audit giornaliero 08:00 UTC → release Docker → docs VitePress → `slopless` |
| Distribuzione | MIT · GHCR · GitHub Pages · 2 stelle · 0 issue aperte · nessun tag/release |

Il progetto **non ha un problema di impalcatura**: test, CI, Docker, docs e hardening
(CSP, privacy, SARIF) sono già a posto e curati. Ha un problema diverso, e più
redditizio da risolvere.

---

## 2. La diagnosi in una riga

> **Cinque funzionalità documentate nel README — sette chiavi di configurazione —
> non esistono nel codice. Un bug distrugge silenziosamente le personalizzazioni
> dell'utente. E il monitor di punta, WHOIS, fallisce proprio dove il progetto
> gira di più: container e CI.**

I quick win più redditizi qui **non sono nuove feature**. Sono *allineare il codice
a ciò che il README promette già*. Ogni riga di questo lavoro converte una promessa
esistente in qualcosa che funziona davvero — impatto massimo, superficie di
progettazione zero.

---

## 3. I quick win, ordinati per ROI

ROI = (impatto su affidabilità · fiducia · adozione) ÷ sforzo.

| # | Quick win | Sforzo | Impatto | ROI |
|---|---|---|---|---|
| **1** | Exit code significativi per la CI | 30 min | Sblocca il caso d'uso CI/CD documentato | ⭐⭐⭐⭐⭐ |
| **2** | Pinning delle dipendenze + Dependabot | 30 min | Protegge l'audit giornaliero | ⭐⭐⭐⭐⭐ |
| **3** | Collegare le 7 chiavi di config morte | 2 h | Elimina 5 feature fantasma | ⭐⭐⭐⭐⭐ |
| **4** | Smettere di sovrascrivere il template | 1 h | Elimina una perdita di dati silenziosa | ⭐⭐⭐⭐⭐ |
| **5** | Rendere il report davvero *self-contained* | 2 h | Verità + supply chain + privacy | ⭐⭐⭐⭐⭐ |
| **6** | Docker: utente non-root + `.dockerignore` | 20 min | Credibilità di un tool di sicurezza | ⭐⭐⭐⭐⭐ |
| **7** | `encoding="utf-8"` esplicito (6 punti) | 15 min | Previene crash su locale non-UTF8 | ⭐⭐⭐⭐ |
| **8** | RDAP prima di WHOIS | 3 h | Il guadagno di affidabilità più grande | ⭐⭐⭐⭐⭐ |
| **9** | Scansione in parallelo | 2 h | Stimato 5–10× sul tempo di scansione | ⭐⭐⭐⭐ |
| **10** | SECURITY.md, CONTRIBUTING.md, primo tag | 1 h | Riduce l'attrito all'adozione | ⭐⭐⭐⭐ |
| **11** | Chiave API opzionale sull'endpoint `/analyze` | 1 h | Chiude un trigger di scansione aperto | ⭐⭐⭐ |
| **12** | Storico dei report + `retention_days` | 2 h | Abilita i trend | ⭐⭐⭐ |
| **13** | `ruff` + coverage in CI | 45 min | Qualità continua | ⭐⭐⭐ |
| **14** | `SSLMonitor`: onorare il parametro `port` | 30 min | Corregge un parametro ignorato | ⭐⭐ |
| **15** | Blacklist: gestire IPv6 e IP multipli | 1 h | Copertura | ⭐⭐ |

**Totale: circa 2–3 giornate di lavoro** per l'intero elenco.

---

## 4. Il piano, in quattro lotti

### Lotto 0 — «Un'ora e mezza, rischio zero» → #1, #2, #6, #7
Nessuna modifica di logica. Solo configurazione, pinning e igiene.
Mergeabile subito, senza discussione di design.

### Lotto 1 — «Verità nel prodotto» → #3, #4, #5
Il lotto a ROI più alto. Non aggiunge nulla: fa funzionare ciò che il README
già dichiara. Alla fine di questo lotto, ogni riga della documentazione è vera.

### Lotto 2 — «Affidabilità e velocità» → #8, #9
I due interventi che si notano davvero nell'uso quotidiano: il monitor dominio
smette di fallire, e l'audit passa da minuti a secondi.

### Lotto 3 — «Adozione e sicurezza» → #10, #11, #12, #13
Il lotto che trasforma un progetto personale ben fatto in qualcosa che altri
adottano con fiducia.

**Backlog:** #14, #15, più la pulizia dei commenti-brainstorming e dei tipi di
ritorno incoerenti in `src/utils/dns_helpers.py`.

---

## 5. Schede di dettaglio

### #1 — Exit code significativi per la CI · 30 min · rischio nullo

**Il problema.** `src/cli.py` chiama `sys.exit()` solo in due punti (righe 166 e
171) e solo per errori di configurazione. Dopo una scansione riuscita il processo
esce **sempre con 0**, anche con certificati scaduti e domini in blacklist.

**Perché conta.** Il README documenta l'integrazione CI/CD come caso d'uso
primario. Oggi nessuna pipeline può fallire su un finding: l'audit gira, trova
problemi critici, e la build resta verde.

**Il fix — fatto.** `--fail-on {never,warning,critical}` (default `never`, per non
rompere chi c'è già) con uscita `0` / `1` / `2`, e `3` riservato a «non ho potuto
eseguire» (config illeggibile, argomenti errati) — anche per gli errori di usage
di argparse, che altrimenti uscirebbero con `2` come i finding critici. Più
`--json` su stdout per il piping verso `jq`.

---

### #2 — Pinning delle dipendenze · 30 min · rischio nullo

**Il problema.** `requirements.txt` elenca 14 dipendenze **senza un solo vincolo
di versione**. `fastapi`, `pyyaml`, `dnspython`, `python-whois`, `pydantic-settings`…
tutte flottanti.

**Perché conta.** L'audit gira automaticamente ogni giorno alle 08:00 UTC. Una
release breaking a monte rompe la scansione notturna senza che nessuno abbia
toccato il repository — e le build Docker non sono riproducibili.

**Il fix.** Pinnare con `==`, aggiungere `.github/dependabot.yml` (oggi `.github/`
contiene solo `workflows/`). Gli aggiornamenti diventano PR revisionabili invece
che sorprese notturne.

---

### #3 — Collegare le sette chiavi di config morte · 2 h · rischio basso

**Il problema — verificato con grep sull'intero codice.**

| Chiave | Documentata in | Letta dal codice? |
|---|---|---|
| `monitors.domain.expiry_warning_days` | README, config.yaml, docs | **No** — fisso a 30 in `constants.py` |
| `monitors.domain.expiry_critical_days` | README, config.yaml, docs | **No** — fisso a 7 |
| `monitors.ssl.expiry_warning_days` | README, config.yaml, docs | **No** — stessi valori fissi |
| `monitors.ssl.expiry_critical_days` | README, config.yaml, docs | **No** — stessi valori fissi |
| `monitors.dns.required_records` | README, config.yaml, docs | **No** — SPF+DMARC cablati |
| `monitors.blacklist.rbls` | docs/guide/monitors.md | **No** — `BlacklistMonitor()` senza argomenti |
| `reports.retention_days` | README, config.yaml, docs | **No** — nulla cancella nulla |

`base_monitor.py` *accetta* `warning_threshold` e `critical_threshold`, ma nessun
chiamante li passa mai: arrivano sempre i default delle costanti.

**Perché conta.** È la peggior classe di bug per un tool guidato da configurazione:
l'utente modifica `expiry_warning_days: 60`, il file viene letto senza errori, e
non cambia niente. Nessun avviso. Nessun modo di accorgersene se non leggendo il
sorgente.

**Il fix.** Passare `monitors_cfg` ai costruttori dei monitor, con i valori di
`constants.py` come default. In più, un warning esplicito per le chiavi di config
sconosciute — così un refuso in YAML si vede subito.

---

### #4 — Smettere di sovrascrivere il template · 1 h · rischio basso

**Il problema.** `HTMLGenerator.__init__` chiama `_create_default_template()`, che
scrive **incondizionatamente** 350 righe di HTML dentro `src/templates/report.html`
a ogni singola istanziazione.

**Verificato sperimentalmente:**
```
$ echo '<!-- MY CUSTOM BRANDING -->' >> src/templates/report.html
$ grep -c "MY CUSTOM BRANDING" src/templates/report.html   →  1
$ python src/cli.py --demo
$ grep -c "MY CUSTOM BRANDING" src/templates/report.html   →  0
```
La personalizzazione è stata distrutta senza un messaggio.

**Perché conta.** Nessuno può adattare il report al proprio brand: la modifica
sparisce alla prima esecuzione. E `html_generator.py` è lungo 467 righe di cui
~350 sono una stringa letterale, il che rende il template impossibile da rivedere
in una diff.

**Il fix.** Distribuire il template come file vero (già presente nel repository) e
scriverlo *solo se manca*. Il file diventa rivedibile, personalizzabile e il
generatore scende sotto le 120 righe.

---

### #5 — Rendere il report davvero *self-contained* · 2 h · rischio basso

**Il problema.** README, `docs/index.md` e `docs/guide/configuration.md` affermano
tutti e tre che i report sono «self-contained». Non lo sono: il template carica
**sette risorse da tre CDN diversi**, nessuna con `integrity`:

```
code.jquery.com        → jquery-3.7.0.min.js
cdn.datatables.net     → dataTables 1.13.6 (CSS + 2 JS) + rowGroup 1.4.1 (CSS + JS)
cdnjs.cloudflare.com   → bootstrap 5.3.0 CSS
```

**Perché conta — quattro ragioni che si sommano:**
1. **La documentazione è falsa** in tre punti.
2. **Offline il report è rotto**: niente tabella, niente ordinamento, niente filtri.
3. **Supply chain**: un tool di sicurezza che carica JavaScript di terze parti non
   verificato dentro una pagina che elenca le debolezze della tua infrastruttura.
4. **Privacy**: tre CDN vedono *chi* legge il report e *quando* — ed è esattamente
   la classe di problema che questo repository ha già corretto due volte
   (`b03a171` sui Google Fonts, `bb27e31` sullo screenshot).

**Il fix.** Incorporare gli asset nel template (il report resta un file singolo, e
l'affermazione diventa vera). Se si preferisce restare sui CDN, allora almeno
`integrity` + `crossorigin` su tutti e sette, e correggere la documentazione.

---

### #6 — Hardening Docker · 20 min · rischio nullo

**Il problema.** Il `Dockerfile` non ha una direttiva `USER`: il container gira
**come root**. E non esiste un `.dockerignore`, quindi `COPY . .` copia dentro
l'immagine `.git` (intera cronologia), `screenshot.png` (1,1 MB), `docs/`,
`node_modules/` e `venv/`.

**Il fix.** Un utente non privilegiato più un `.dockerignore`. Venti minuti per
un'immagine più piccola, più pulita e che non gira da root — su un progetto il cui
argomento è la sicurezza.

---

### #7 — `encoding="utf-8"` esplicito · 15 min · rischio nullo

**Il problema.** Sei `open()` senza `encoding` esplicito, quindi dipendenti dal
locale: lettura config (`cli.py:161`), scrittura template
(`html_generator.py:18`), scrittura `index.html` (`:460`), scrittura `report.json`
(`:464`), lettura/scrittura dello stato notifiche (`manager.py:21,31`).

**Perché conta.** Un nome di registrar WHOIS non-ASCII su un sistema con locale non
UTF-8 fa fallire la generazione del report con `UnicodeEncodeError` — dopo che
tutta la scansione è già stata eseguita.

---

### #8 — RDAP prima di WHOIS · 3 h · rischio medio

**Il problema — misurato in questo container:**
```
dns          0.03s  ok
ssl          0.05s  warning
security     0.23s  error
blacklist    0.17s  ok
domain      10.02s  error      ←  WHOIS
```
Il monitor dominio impiega **10 secondi per fallire**. WHOIS usa la porta 43, che è
bloccata in moltissimi container, runner CI e reti aziendali. In più è soggetto a
rate limiting e restituisce testo non strutturato, che `python-whois` deve
interpretare con parser fragili, registrar per registrar.

**Perché conta.** È il monitor di punta — il primo elencato nel README — e il più
fragile proprio negli ambienti in cui il progetto è pensato per girare.

**Il fix.** RDAP come percorso primario, WHOIS come fallback. RDAP è lo standard
IETF che sostituisce WHOIS (RFC 9083): HTTPS sulla 443 (passa dai proxy), JSON
strutturato (niente parsing fragile), bootstrap via `rdap.org`. Circa 50 righe per
il guadagno di affidabilità più grande dell'intero elenco.

---

### #9 — Scansione in parallelo · 2 h · rischio basso

**Il problema.** `cli.py` cicla sui domini **uno alla volta**, e dentro ogni dominio
esegue i cinque monitor **uno alla volta**. Con i 7 domini di `config.yaml` sono 35
operazioni di rete bloccanti in serie.

**Il bello è che il pattern esiste già.** `api/api.py` fa esattamente la cosa giusta:
```python
outputs = await asyncio.gather(
    *(asyncio.to_thread(func, req.domain) for _, func in checks)
)
```
Non è stato applicato alla CLI.

**Il fix.** Riusare quel pattern nella CLI con un semaforo per limitare la
concorrenza (gentilezza verso i server WHOIS e i resolver DNS). Riduzione stimata
del tempo di scansione: **5–10×**.

---

### #10 — Governance e primo rilascio · 1 h · rischio nullo

**Il problema.** Mancano `SECURITY.md` (su un tool di sicurezza), `CONTRIBUTING.md`,
`CHANGELOG.md` e i template per le issue. E `git tag` è vuoto: il workflow di
release è già cablato su `v*.*.*` ma **non è mai stato tagliato un rilascio**,
quindi non esiste una versione citabile né un'immagine `ghcr.io` versionata.

**Il fix.** I quattro file più `git tag v1.0.0`. Il workflow esistente fa il resto
da solo.

---

### #11 — Chiave API opzionale · 1 h · rischio basso

`POST /analyze` non ha autenticazione. Chiunque possa raggiungere la porta può far
partire scansioni WHOIS/TLS/HTTP verso domini arbitrari dal tuo host — un trigger di
scansione in uscita aperto. È mitigato (rate limit 10/min per IP, e
`docker-compose.yml` lo lega a 127.0.0.1), ma il `CMD` di default del Dockerfile
espone `0.0.0.0:8000`: chi fa `docker run` seguendo il README lo pubblica in chiaro.

**Il fix.** Un `DOMAINMATE_API_KEY` opzionale: se impostato, si esige l'header; se
non impostato, comportamento invariato.

---

### #12 — Storico dei report · 2 h · rischio basso

Ogni esecuzione sovrascrive `reports/index.html` e `reports/report.json`. Non esiste
storico, quindi non esistono trend, né confronto con ieri, né grafico delle scadenze
che si avvicinano. `retention_days: 30` in config lascia intendere che lo storico
fosse previsto fin dall'inizio.

**Il fix.** Scrivere anche `report-YYYYMMDD-HHMM.json`, con pulizia guidata da
`retention_days` — che chiude anche l'ultima chiave di config morta del punto #3.

---

## 6. Come misurare il successo

| Metrica | Oggi | Obiettivo |
|---|---|---|
| Chiavi di config documentate ma non funzionanti | 7 | 0 |
| Affermazioni false nella documentazione | 3 (`self-contained`) | 0 |
| Richieste di rete di terze parti aprendo un report | 7 | 0 |
| Tempo di scansione, 7 domini | sequenziale | 5–10× più veloce |
| Tasso di successo del monitor dominio in container | fallisce in 10 s | RDAP su 443 |
| Dipendenze non pinnate | 14 | 0 |
| Il container gira come root | sì | no |
| Release taggate | 0 | v1.0.0 |

---

## 7. La raccomandazione

Partire dal **Lotto 0** (un'ora e mezza, nessuna modifica di logica, mergeabile
oggi) e poi dedicare una giornata piena al **Lotto 1**.

Il Lotto 1 è il vero affare. Non aggiunge una sola feature: prende **sette
promesse** che il README fa già — soglie dominio, soglie SSL, record DNS richiesti,
RBL personalizzate, retention, template personalizzabile, report self-contained —
e le rende vere. Per un progetto open source con due stelle e zero
issue aperte, la cosa più preziosa non è avere più funzionalità. È che ogni
funzionalità dichiarata funzioni davvero quando la prima persona seria decide di
provarla.
