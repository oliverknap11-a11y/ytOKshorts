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
- **Outfit dňa** – tip na oblečenie jedným klikom („Prekvap ma“).
- **AI skúšobňa (voliteľné)** – outfit oblečený na modelovi cez AI (viď [`AI-TRYON.md`](AI-TRYON.md) a [`tryon-proxy/`](tryon-proxy/)).
- **Štítky** sezóna a príležitosť + filtrovanie outfitov podľa nich.
- **Úprava a vyhľadávanie** – kusy môžeš upravovať a hľadať v šatníku.
- **Obľúbené** ❤ – outfity, ktoré sa ti páčia, si označíš a vyfiltruješ.
- **Filtre a miešanie** – filtrovanie podľa kusu/sezóny/príležitosti, náhodné miešanie.
- **Štatistiky** – počet kúskov, možných outfitov a obľúbených.
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

### 3. Natívna appka v App Store – **bez Macu** (odporúčané)
V priečinku [`expo-app/`](expo-app/) je pripravený **Expo** projekt. Appku
zostavíš a nahráš do App Store **cez cloud (EAS Build/Submit), bez Macu**.
Krok‑po‑kroku návod: [`expo-app/EAS-BUILD.md`](expo-app/EAS-BUILD.md).
Potrebuješ len Expo účet (zadarmo) a Apple Developer účet (99 USD/rok).

### 4. Natívna iOS appka cez Capacitor (alternatíva, ak máš Mac)
V priečinku [`ios-app/`](ios-app/) je **Capacitor** projekt a návod
[`ios-app/APP-STORE.md`](ios-app/APP-STORE.md). Táto cesta vyžaduje Mac s Xcode.

Spoločné pre App Store: hotové texty [`store-listing.md`](store-listing.md)
a zásady súkromia [`PRIVACY.md`](PRIVACY.md).

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
| `expo-app/` | **Expo** projekt – App Store bez Macu (cloud build) |
| `ios-app/` | Capacitor projekt – App Store s Macom (alternatíva) |
| `store-listing.md`, `PRIVACY.md` | texty a súkromie pre App Store |
| `co-appka-vie.txt` | popis funkcií po slovensky |

## Technológie

Webová časť je čisté HTML, CSS a JavaScript bez závislostí. Pre App Store sa
appka balí natívnym obalom **Capacitor**.
