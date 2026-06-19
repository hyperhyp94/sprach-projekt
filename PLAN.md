# PLAN.md — Vokabel-Trainer mit Anki-ähnlichem Spaced-Repetition

Architekturplan für den Umbau von `index.html` von einer reinen Download-Seite
zu einer interaktiven SRS-Lern-App. **Kein Code** — nur Architektur.

> **Grundregel:** `server.py` bleibt UNANGETASTET. Das SM-2-Backend ist fertig
> und funktioniert. Das gesamte Frontend (State, SRS-Loop, UI) lebt in `index.html`.

---

## 1. Dateiliste

| Datei | Status | Beschreibung |
|-------|--------|--------------|
| `server.py` | **UNVERÄNDERT** | Flask-Backend mit SM-2, alle API-Endpunkte fertig |
| `data/vocab_de.json` | **UNVERÄNDERT** | 66 ES + 69 TR Vokabeln, 6 Kategorien je Sprache |
| `data/progress.json` | **UNVERÄNDERT (Laufzeit)** | Wird ausschließlich vom Server geschrieben |
| `static/a1-es.apkg` | **UNVERÄNDERT** | Anki-Fallback-Download (optional in Footer verlinken) |
| `static/a1-tr.apkg` | **UNVERÄNDERT** | Anki-Fallback-Download |
| `index.html` | **KOMPLETT NEU** | Single-File-App: HTML + Tailwind CDN + Vanilla JS inline |
| `PLAN.md` | **NEU** | Dieses Dokument |

**Keine** neuen JS-/CSS-Dateien — alles inline in `index.html` (keine Build-Step,
keine externen Deps außer Tailwind CDN). Backend benötigt nur das bereits
installierte Flask.

---

## 2. Backend-Verträge (Referenz — wird nur konsumiert)

Diese Endpunkte existieren bereits und definieren den Datenfluss:

| Methode | Endpoint | Zweck | Antwort (Kern) |
|---------|----------|-------|----------------|
| `GET` | `/api/categories?lang=es\|tr` | Kategorienamen | `["Begrüßung", ...]` |
| `GET` | `/api/vocab?lang=&category=` | Alle Karten (Modus „Alle") | `[{word, translation, category}]` |
| `GET` | `/api/due?lang=&category=` | Fällige + neue Karten + Stats | `{due:[…], new_cards:[…], stats:{…}}` |
| `GET` | `/api/progress?lang=` | Initialisiert State neuer Karten | `{word: {state}}` |
| `POST`| `/api/progress` | Bewertung speichern → SM-2 | neuer State |

**`/api/due` ist der Kern-Endpoint** des SRS-Modus. Er liefert:
- `due[]` — fällige + neue Karten, sortiert (älteste Fälligkeit zuerst), je mit `state`
- `new_cards[]` — Teilmenge der noch nie gelernten Karten
- `stats` — `due_count`, `new_count`, `total_count`, `reviewed_count`, `next_due` (ISO)

**POST-Body:** `{lang, word, rating}` mit `rating ∈ {0, 2, 3, 5}`.
Mapping der 4 Knöpfe → Rating:

| Button | Label | Rating (q) | Backend-Verhalten |
|--------|-------|-----------|-------------------|
| 🔴 | Wiederholen | `0` | Reset, +10 min |
| 🟠 | Schwer | `2` | Reset, +1 Tag, EF −0.2 |
| 🟢 | Gut | `3` | SM-2-Standard |
| 🔵 | Leicht | `5` | EF +0.15, Intervall ×1.3 |

---

## 3. UI-Skizze (Mobile-First, min 320px)

```
┌─────────────────────────────────┐
│  HEADER (sticky)                 │
│  📚 Vokabel-Trainer              │
│  [🇪🇸 ES] [🇹🇷 TR]   ← Sprachwahl │
├─────────────────────────────────┤
│  STATS-LEISTE (immer sichtbar)   │
│  Fällig 12 · Neu 8 · Gel. 40 ·   │
│  Gesamt 66                       │
├─────────────────────────────────┤
│  STEUERUNG                       │
│  [Kategorie ▼] (Dropdown)        │
│  [SRS-Modus] [Alle Karten]       │
│  [🔀 Mischen] [➕ Neue Karten]   │
├─────────────────────────────────┤
│                                  │
│  KARTE (Flip-Card)               │
│  ┌───────────────────────────┐   │
│  │  Kategorie · 3/12         │   │
│  │                           │   │
│  │       hola                │   │  ← Vorderseite (word)
│  │                           │   │
│  │   [ Antwort zeigen ]      │   │  ← Tap-Ziel ≥44px
│  └───────────────────────────┘   │
│                                  │
│  Nach Flip: Rückseite +          │
│  4 Bewertungs-Buttons:           │
│  ┌─────┬─────┬─────┬─────┐       │
│  │🔴Wdh│🟠Sch│🟢Gut│🔵Lei│       │  ← je ≥44px hoch
│  └─────┴─────┴─────┴─────┘       │
│                                  │
├─────────────────────────────────┤
│  LEER-ZUSTAND (wenn 0 fällig)    │
│  🎉 Alles gelernt! Nächste       │
│  Wiederholung: in 2 Std          │
├─────────────────────────────────┤
│  FOOTER: Anki-Decks (.apkg)      │
└─────────────────────────────────┘
```

### Komponenten-Übersicht
1. **Header** (sticky top): Titel + Sprach-Toggle (zwei Buttons, aktiver hervorgehoben).
2. **Stats-Leiste**: 4 Zahlen aus `stats`. Aktualisiert nach jeder Bewertung.
3. **Steuerung**: Kategorie-Dropdown, Modus-Umschalter (SRS ⟷ Alle), Mischen, Neue-Karten.
4. **Karten-Bereich**: Flip-Card; vorne `word`, hinten `translation`; danach Rating-Buttons.
5. **Leer-/End-Zustand**: Glückwunsch + `next_due` (relativ formatiert), Button „Alle Karten lernen".
6. **Footer**: dezente Links zu den `.apkg`-Downloads (Anki-Fallback).

### Mobile-First-Regeln
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` (kein `maximum-scale`, damit Zoom möglich bleibt — Accessibility).
- Alle interaktiven Elemente: `min-height:44px`, ausreichend horizontaler Padding, `min-width` für Touch.
- Container `max-w-md`/`max-w-2xl mx-auto`, Layout funktioniert ab 320px.
- Rating-Buttons als responsives Grid (4 Spalten auf breit, 2×2 sehr eng falls nötig).
- Große, gut lesbare Schrift für das Vokabel-Wort; hoher Kontrast.

---

## 4. Datenfluss (Progress laden / speichern)

```
                         ┌──────────────────────────┐
   App-Start / Sprach-   │  GET /api/progress?lang   │  → initialisiert State
   wechsel               │  (Server legt neue Karten │    für neue Karten
                         │   in progress.json an)    │
                         └────────────┬─────────────┘
                                      ▼
   Queue laden    ┌──────────────────────────────────────┐
   (SRS-Modus)    │  GET /api/due?lang=&category=         │ → due[], new_cards[], stats
                  └────────────┬─────────────────────────┘
                               ▼
                  Frontend-Queue = due[]  (Reihenfolge vom Server)
                               ▼
              ┌────────────► Karte anzeigen (Front) ◄───────────┐
              │                    │ Tap „Antwort zeigen"        │
              │                    ▼                             │
              │             Rückseite + Rating-Buttons           │
              │                    │ Tap Rating                  │
              │                    ▼                             │
              │      POST /api/progress {lang,word,rating}       │
              │      (Server rechnet SM-2, schreibt progress.json)│
              │                    │ Antwort: neuer State        │
              │                    ▼                             │
              │      Stats lokal aktualisieren, Karte aus Queue  │
              └──────────── nächste Karte / Queue leer? ─────────┘
                               ▼ (Queue leer)
                  GET /api/due erneut → Refresh Stats + ggf. neue Runde
```

**Persistenz-Prinzip:**
- Das Frontend hält **keinen** dauerhaften Zustand — `progress.json` ist die
  einzige Quelle der Wahrheit, ausschließlich serverseitig geschrieben.
- Jede Bewertung ist ein synchroner POST; erst nach Erfolg geht es zur nächsten Karte
  (verhindert Datenverlust). Optional: optimistisches Weiterschalten mit Rollback bei Fehler.
- Nach Reload/Session-Wechsel liefert `/api/due` automatisch den korrekten Zustand —
  kein `localStorage` nötig.

---

## 5. JavaScript-Architektur

Vanilla JS, inline in `index.html`. Keine Frameworks. Aufbau in klar getrennten
Verantwortlichkeiten (logische „Module" als Funktionsgruppen, kein Bundler).

### 5.1 State-Objekt (zentral, in-memory)
Ein einziges `state`-Objekt als Single Source of Truth des UI:

| Feld | Bedeutung |
|------|-----------|
| `lang` | aktuelle Sprache `"es"` / `"tr"` |
| `category` | aktueller Filter (`"all"` oder Kategoriename) |
| `mode` | `"srs"` (nur fällige) oder `"all"` (alle Karten) |
| `queue` | Array der aktuell zu lernenden Karten |
| `index` | Position in `queue` (aktuelle Karte) |
| `flipped` | bool — ist die Rückseite sichtbar? |
| `stats` | letzte Stats vom Server |
| `loading` | bool — verhindert Doppel-Aktionen während Requests |

Persistente UI-Präferenzen (`lang`, `category`, `mode`) optional in `localStorage`
gespiegelt — **nur Bequemlichkeit**, nie Lernfortschritt.

### 5.2 Funktionsgruppen
1. **API-Layer** — dünne `fetch`-Wrapper je Endpoint (`fetchDue`, `fetchVocab`,
   `fetchCategories`, `initProgress`, `postRating`). Einheitliches Error-Handling +
   JSON-Parsing. Geben Promises zurück.
2. **State-Aktionen** — reine Funktionen, die `state` verändern und danach `render()`
   aufrufen (z. B. `loadQueue()`, `nextCard()`, `flipCard()`, `setLang()`,
   `setCategory()`, `setMode()`, `shuffleQueue()`, `submitRating(q)`).
3. **Render-Layer** — `render()` zeichnet UI aus `state` (deklarativ: DOM spiegelt
   immer `state`). Teil-Renderer: `renderStats()`, `renderCard()`, `renderControls()`,
   `renderEmptyState()`. Kein verstreutes DOM-Gefummel in Event-Handlern.
4. **Utils** — `formatRelative(iso)` für `next_due` („in 2 Std"), `shuffle(arr)`
   (Fisher–Yates), `mapButtonToRating()`.

### 5.3 Event-Handling
- **Event-Delegation** auf einem Container statt vieler Einzel-Listener.
- Aktionen via `data-action`-Attribute (`data-action="flip"`,
  `data-action="rate" data-rating="3"`, `data-action="set-lang" data-lang="tr"` …).
- Buttons während laufendem Request deaktiviert (`state.loading`) → keine Doppel-POSTs.
- Optional Tastatur (Desktop): Space = Flip, 1–4 = Ratings (Progressive Enhancement).

### 5.4 Initialisierung (Bootstrap-Sequenz)
1. `state` aus Defaults (+ optional `localStorage`-Präferenzen) aufbauen.
2. `initProgress(lang)` → stellt sicher, dass neue Karten serverseitig State haben.
3. `fetchCategories(lang)` → Dropdown füllen.
4. `loadQueue()` → `fetchDue()` → `queue` + `stats` setzen.
5. `render()` → erste Karte zeigen.

---

## 6. SM-2-Flow im Frontend (Lern-Loop)

```
loadQueue()
   └─ GET /api/due → state.queue = due[], state.index = 0, state.stats = stats
        │
        ▼
   render() zeigt queue[index], Vorderseite (word), flipped=false
        │
   User tippt „Antwort zeigen"  → flipCard(): state.flipped=true → render()
        │   (zeigt translation + 4 Rating-Buttons)
        ▼
   User tippt Rating-Button (Wdh/Schwer/Gut/Leicht)
        │
   submitRating(q):
     1. state.loading=true, Buttons sperren
     2. POST /api/progress {lang, word: aktuelleKarte, rating: q}
     3. Erfolg → Stats anpassen (reviewed++ / due-- / new--), state.loading=false
     4. nextCard(): index++, flipped=false
        │
        ▼
   index < queue.length ?
     • ja  → render() nächste Karte
     • nein→ loadQueue() erneut (holt evtl. neu fällig gewordene + frische Stats)
             └─ queue leer → renderEmptyState() (🎉 + next_due relativ)
```

**Sonderfälle:**
- **Rating „Wiederholen" (q=0):** Server setzt `next_review` auf +10 min. Die Karte
  ist damit i. d. R. nicht mehr in derselben Runde fällig. (Optionales Komfort-Feature:
  Karte ans Queue-Ende anhängen — rein clientseitig, ohne Backend-Änderung.)
- **Modus „Alle Karten":** `loadQueue()` nutzt `GET /api/vocab` statt `/api/due`;
  Bewertungen werden weiterhin via POST gespeichert (kein Fälligkeits-Filter).
- **„Neue Karten"-Button:** filtert/priorisiert `new_cards` aus der `/api/due`-Antwort
  in die Queue — rein clientseitige Auswahl, kein neuer Endpoint.
- **„Mischen":** `shuffle(state.queue)` (Fisher–Yates), `index=0`, `render()`.
- **Sprach-/Kategorie-Wechsel:** komplettes `loadQueue()` mit neuen Parametern.
- **POST-Fehler/Offline:** Karte bleibt, Buttons wieder aktiv, dezente Fehlermeldung;
  Fortschritt geht nicht verloren (kein optimistisches Verwerfen).

---

## 7. Mobile-First & Accessibility-Checkliste (Design-Vorgaben)

- [ ] Viewport-Meta vorhanden, Zoom nicht unterbunden (`maximum-scale` weglassen).
- [ ] Alle Buttons/Links ≥ 44×44px Touch-Ziel.
- [ ] Layout bricht nicht unter 320px Breite.
- [ ] Stats-Leiste auf allen Größen lesbar (umbrechend statt abgeschnitten).
- [ ] Hoher Kontrast, große Vokabel-Schrift.
- [ ] Aktiver Sprach-/Modus-Button klar visuell hervorgehoben.
- [ ] Ladezustand sichtbar (Spinner/Skeleton), gesperrte Buttons während Requests.
- [ ] `aria-label`/Rollen für Icon-Buttons; Tastatur-Navigation funktioniert.

---

## 8. Test-Checkliste

### Backend-Smoke (bereits fertig — nur verifizieren, nicht ändern)
- [ ] `python server.py` startet auf Port 5111 (bzw. `TOOL_PORT`).
- [ ] `GET /api/categories?lang=es` → 6 Kategorien; `lang=tr` ebenso.
- [ ] `GET /api/due?lang=es&category=all` → `due`, `new_cards`, `stats` plausibel.
- [ ] `POST /api/progress {lang:"es",word:"hola",rating:3}` → neuer State; `progress.json` aktualisiert.
- [ ] Ungültiges Rating (z. B. 1) → HTTP 400.

### Frontend — Funktion
- [ ] App lädt, Default-Sprache ES, erste fällige Karte erscheint.
- [ ] „Antwort zeigen" flippt Karte → Übersetzung + 4 Rating-Buttons.
- [ ] Jeder der 4 Buttons sendet korrektes Rating (0/2/3/5) und schaltet weiter.
- [ ] Stats-Leiste aktualisiert sich nach jeder Bewertung.
- [ ] Queue leer → 🎉 Leer-Zustand mit relativer `next_due`-Zeit.
- [ ] Sprachwechsel 🇪🇸↔🇹🇷 lädt korrekte Vokabeln + Kategorien + Stats neu.
- [ ] Kategorie-Filter schränkt Queue korrekt ein.
- [ ] Modus „Alle Karten" zeigt alle Vokabeln (auch nicht-fällige).
- [ ] „Mischen" ändert Reihenfolge, startet bei Karte 1.
- [ ] „Neue Karten" priorisiert ungelernte Karten.

### Persistenz (Kernanforderung)
- [ ] Karte bewerten → Browser-Reload → Karte ist nicht mehr fällig (Fortschritt blieb).
- [ ] Server neu starten → `/api/due` liefert weiterhin korrekten Zustand.
- [ ] `progress.json` enthält nach Bewertungen aktualisierte `ease_factor`/`interval_days`/`next_review`.

### Mobile / Robustheit
- [ ] DevTools 320px-Breite: kein horizontales Scrollen, alles bedienbar.
- [ ] Touch-Ziele ≥44px (real auf Smartphone testen).
- [ ] Doppel-Tap auf Rating erzeugt keinen Doppel-POST (Loading-Sperre greift).
- [ ] Server offline → verständliche Fehlermeldung, kein „toter" UI-Zustand.
- [ ] Footer-Links zu `.apkg`-Decks funktionieren weiterhin.

---

## 9. Nicht-Ziele / Grenzen

- **Kein** Anfassen von `server.py`, `vocab_de.json`, `progress.json`-Logik.
- **Keine** neuen Dependencies, Build-Tools oder Frameworks (nur Tailwind CDN + Vanilla JS).
- **Kein** clientseitiges SM-2 — die gesamte Algorithmik bleibt im Backend.
- **Keine** Arbeit außerhalb von `/home/sven/hermes-workspace/projects/vokabel-trainer`.
- Umfang bleibt A1 (135 Vokabeln, 2 Sprachen, 6 Kategorien je Sprache).
