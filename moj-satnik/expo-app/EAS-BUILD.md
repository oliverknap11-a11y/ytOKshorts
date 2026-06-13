# Publikovanie do App Store cez Expo (BEZ Macu) 🚀

Toto je odporúčaná cesta, keď **nemáš Mac**. Expo službou **EAS Build**
skompiluje iOS appku v cloude a **EAS Submit** ju nahrá do App Store –
všetko z Windowsu/Linuxu, bez Xcode.

> Čo stále potrebuješ: **Expo účet** (zadarmo, už ho máš) a na publikovanie
> **Apple Developer účet** (99 USD/rok). Apple Developer účet je podmienka Apple
> pre akúkoľvek appku v App Store – cloud build cez Expo ho nenahrádza, ale
> vďaka nemu nepotrebuješ Mac.

---

## 1) Nainštaluj EAS CLI a prihlás sa

```bash
npm install -g eas-cli       # alebo používaj "npx eas-cli ..." bez inštalácie
eas login                    # prihlás sa svojím Expo účtom
```

## 2) Priprav projekt

V tomto priečinku (`moj-satnik/expo-app/`):

```bash
npm install                  # závislosti
npm run build:html           # zabalí webovú appku do assets/app-html.js
```

> `npm run build:html` spusti vždy, keď zmeníš webovú appku (`../index.html`),
> aby sa zmena dostala do mobilnej appky.

Prepoj projekt so svojím Expo účtom (vytvorí/­priradí EAS Project ID):

```bash
eas init
```

## 3) Vyskúšaj appku ešte pred buildom (voliteľné, rýchle)

Bez buildu si appku otvoríš v mobile cez **Expo Go**:

```bash
npx expo start
```

Naskenuj QR kód appkou **Expo Go** (z App Store) na svojom iPhone.
Takto hneď vidíš, či sa dá pridať oblečenie a poskladať outfity.

> Pozn.: výber fotiek z galérie naplno funguje až v reálnom builde (krok 4),
> nie vždy v Expo Go.

## 4) Build iOS appky v cloude (žiaden Mac)

```bash
eas build --platform ios --profile production
```

EAS sa cez terminál spýta na prihlásenie k Apple účtu a **automaticky vytvorí
podpisové certifikáty a provisioning profily** (stačí potvrdiť „Yes“).
Build prebehne na serveroch Expo – na konci dostaneš `.ipa` súbor.

> Ak chceš appku najprv len otestovať na svojom iPhone, použi profil
> `--profile preview` a nainštaluj si ju cez TestFlight (krok 5).

## 5) Nahraj appku do App Store Connect

```bash
eas submit --platform ios --latest
```

EAS nahrá posledný build do App Store Connect (potrebuje prístup k Apple účtu;
prvýkrát ťa prevedie nastavením, ideálne cez **App Store Connect API key**).
Po nahraní sa build objaví v **TestFlight** aj pri verzii v App Store Connect.

## 6) Dokonči záznam a pošli na schválenie

Na https://appstoreconnect.apple.com pri appke **Môj šatník**:

- **Screenshots** (povinné, 6.7"/6.9" iPhone) – pozri tip nižšie.
- **Popis, Keywords, Promotional text** → skopíruj z [`../store-listing.md`](../store-listing.md).
- **Privacy Policy URL** → zverejni [`../PRIVACY.md`](../PRIVACY.md) napr. cez GitHub Pages a vlož adresu.
- **App Privacy** → *Data Not Collected* (appka nezbiera žiadne dáta).
- **Pricing** → Free. **Age rating** → 4+.
- Nakoniec **Add for Review → Submit**. Schválenie zvyčajne trvá 1–3 dni.

---

## Ako spraviť screenshoty bez Macu

1. Nainštaluj si appku na svoj iPhone cez **TestFlight** (po `eas submit`).
2. Sprav klasické screenshoty priamo v telefóne (bočné tlačidlo + hlasitosť).
3. Použi iPhone s veľkým displejom (Pro Max), aby rozmery sedeli na 6.7"/6.9".

---

## Aktualizácia appky neskôr

```bash
npm run build:html                                   # ak si menil web appku
eas build --platform ios --profile production        # nový build
eas submit --platform ios --latest                   # nahrať
```

Číslo buildu rieši EAS automaticky (`autoIncrement` v `eas.json`).
Pri väčšej zmene zvýš `version` v `app.json` (napr. `1.0.0` → `1.1.0`).

---

## ⚠️ Aby appku neodmietli (Guideline 4.2)

Appka má reálnu funkčnosť (funguje offline, ukladá šatník, generuje
kombinácie), takže má dobrú šancu prejsť. Pre istotu zdôrazni v popise, že
**funguje offline** a **dáta ostávajú v telefóne**, a pridaj pekné screenshoty
so skutočným obsahom (nie prázdny šatník).
