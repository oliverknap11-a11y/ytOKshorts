# Môj šatník – kombinátor outfitov

Jednoduchá webová aplikácia, do ktorej nahádžeš fotky alebo odkazy na svoje oblečenie
a ona ti automaticky poskladá **všetky kombinácie outfitov** ako obrázkové karty.

## Čo vie

- **Pridávanie oblečenia** – fotka z počítača/mobilu (aj viac naraz, drag & drop),
  priamy odkaz na obrázok (URL) alebo odkaz na produkt v e-shope.
- **Kategórie**
  - Spodné diely: nohavice, rifle, sukňa, skort, kraťasy
  - Vrchné diely: tričko, top, vesta, bunda, mikina, sako
  - Šaty (počítajú sa ako samostatný celý outfit)
- **Outfity** – každý vrchný diel sa skombinuje s každým spodným dielom,
  šaty sa zobrazia ako samostatné outfity.
- **Obľúbené** ❤ – outfity, ktoré sa ti páčia, si označíš a vyfiltruješ.
- **Filtre a miešanie** – filtrovanie podľa konkrétneho kusu, náhodné zamiešanie poradia.
- **Záloha** – export/import šatníka do JSON súboru.

## Ako to spustiť / nainštalovať

Appku môžeš používať tromi spôsobmi – od najjednoduchšieho po App Store:

### 1. Hneď v prehliadači (zadarmo)
1. Stiahni si súbor `index.html` (alebo celý repozitár).
2. Otvor ho v prehliadači (dvojklik) – funguje na počítači aj v mobile.

### 2. Ako appka na ploche telefónu (PWA, zadarmo, bez App Store)
1. Zapni **GitHub Pages** (Settings → Pages → Deploy from branch → `main`,
   priečinok `/moj-satnik`).
2. Na iPhone otvor adresu v **Safari** → **Zdieľať** → **Pridať na plochu**.
   (Na Androide: Chrome → ponuka → *Inštalovať aplikáciu*.)

Appka sa pridá ako ikona, spúšťa sa na celú obrazovku a funguje offline.
Zabezpečujú to `manifest.webmanifest`, `service-worker.js` a ikony v `icons/`.

### 3. Natívna iOS appka v App Store
V priečinku [`ios-app/`](ios-app/) je pripravený **Capacitor** projekt aj
kompletný návod [`ios-app/APP-STORE.md`](ios-app/APP-STORE.md) (slovensky),
texty pre obchod a zásady súkromia. Publikovanie vyžaduje Mac s Xcode a
Apple Developer účet (99 USD/rok).

---

Všetky dáta (fotky aj obľúbené outfity) sa ukladajú **len lokálne v tvojom
zariadení** – nikam sa neposielajú. Fotky sa pri ukladaní automaticky
zmenšujú, aby sa zmestilo čo najviac kusov.

## Štruktúra

| Cesta | Čo to je |
|-------|----------|
| `index.html` | celá webová appka (HTML + CSS + JS, bez závislostí) |
| `manifest.webmanifest`, `service-worker.js` | PWA – inštalácia na plochu a offline |
| `icons/` | ikony appky a splash (generuje `tools/make-icons.py`) |
| `ios-app/` | Capacitor projekt + návod na App Store |
| `co-appka-vie.txt` | popis funkcií po slovensky |

## Technológie

Webová časť je čisté HTML, CSS a JavaScript bez závislostí. Pre App Store sa
appka balí natívnym obalom **Capacitor**.
