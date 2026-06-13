# Ako dostať „Môj šatník“ do App Store 🍏

Tento návod ťa krok po kroku prevedie zverejnením appky v Apple App Store.
Všetko, čo sa dalo pripraviť vopred, je už hotové – ostávajú len kroky, ktoré
**musia bežať na Macu** (Apple to inak nedovolí).

---

## 0) Čo budeš potrebovať (jednorazovo)

| Vec | Detail | Cena |
|-----|--------|------|
| **Apple Developer účet** | https://developer.apple.com/programs/ – registrácia firmy alebo jednotlivca | **99 USD / rok** |
| **Mac s macOS** | Xcode beží len na macOS | – |
| **Xcode 16 alebo novší** | zadarmo v Mac App Store | – |
| **CocoaPods** | `sudo gem install cocoapods` (alebo `brew install cocoapods`) | – |
| **Node.js 20+** | https://nodejs.org | – |

> Bez Apple Developer účtu (99 USD/rok) a Macu sa do App Store publikovať **nedá** –
> je to podmienka Apple, nie tejto appky. Ak appku chceš len pre seba zadarmo,
> pozri sekciu „Lacnejšia alternatíva“ úplne dole.

---

## 1) Priprav projekt (na Macu)

V priečinku `moj-satnik/ios-app/`:

```bash
npm install            # stiahne Capacitor
npm run ios:add        # skopíruje appku do www/ a vytvorí natívny iOS projekt
npm run ios:assets     # vygeneruje všetky veľkosti ikon + splash z ../icons
npm run ios:open       # otvorí projekt v Xcode
```

Kedykoľvek neskôr zmeníš webovú appku (`../index.html`), stačí:

```bash
npm run ios:sync       # prekopíruje zmeny do natívneho projektu
```

---

## 2) Nastav appku v Xcode

Po `npm run ios:open` sa otvorí Xcode. V ľavom paneli klikni na **App** → záložka
**Signing & Capabilities**:

1. **Team** – vyber svoj Apple Developer tím (prihlás sa cez Xcode → Settings → Accounts).
2. **Bundle Identifier** – `com.mojsatnik.app`
   - Musí byť **celosvetovo jedinečný**. Ak ti Apple povie, že je obsadený,
     zmeň ho (napr. `com.tvojemeno.satnik`) aj v súbore `capacitor.config.json`.
3. Zaškrtni **Automatically manage signing** (najjednoduchšie).

Potom v záložke **General**:

- **Display Name:** `Môj šatník`
- **Version:** `1.0.0` (verzia pre používateľa)
- **Build:** `1` (pri každom novom uploade zvýš o 1)
- **Deployment Target:** iOS 14.0 alebo vyššie

---

## 3) Over appku v simulátore

Hore v Xcode vyber napr. „iPhone 16 Pro“ a stlač ▶ (Run). Appka sa spustí
v simulátore – over, že sa dá pridať oblečenie a poskladať outfity.

---

## 4) Vytvor appku v App Store Connect

1. Choď na https://appstoreconnect.apple.com → **My Apps** → **➕ → New App**.
2. Vyplň:
   - **Platform:** iOS
   - **Name:** `Môj šatník` (názov v store, musí byť jedinečný v rámci App Store)
   - **Primary Language:** Slovak
   - **Bundle ID:** vyber `com.mojsatnik.app` (objaví sa po prvom uploade alebo
     ho vytvoríš v *Certificates, Identifiers & Profiles*)
   - **SKU:** ľubovoľný interný kód, napr. `MOJSATNIK001`
3. Texty, kategórie a kľúčové slová nájdeš predvyplnené v **`store-listing.md`**.

---

## 5) Nahraj build (archive)

V Xcode:

1. Hore vyber cieľ **Any iOS Device (arm64)** (nie simulátor).
2. Menu **Product → Archive**. Po dokončení sa otvorí **Organizer**.
3. **Distribute App → App Store Connect → Upload**. Nechaj predvolené voľby,
   podpíš a nahraj.
4. Po pár minútach sa build objaví v App Store Connect (najprv „Processing“).

> Prvý upload appky tam zároveň zaregistruje Bundle ID, ak ešte neexistoval.

---

## 6) Vyplň záznam a pošli na schválenie

V App Store Connect pri verzii **1.0**:

- **Screenshots** – povinné. Najjednoduchšie: spusti appku v simulátore
  „iPhone 16 Pro Max“ a sprav 3–5 screenshotov (⌘S v simulátore).
  Apple vyžaduje 6.7"/6.9" iPhone screenshoty (napr. 1320 × 2868 px).
- **Promotional text, Description, Keywords** → skopíruj z `store-listing.md`.
- **Support URL** a **Privacy Policy URL** → pozri `store-listing.md` a `PRIVACY.md`
  (privacy policy musíš zverejniť na nejakej webovej adrese – stačí GitHub Pages).
- **App Privacy** → klikni *Get Started* a označ **„Data Not Collected“**
  (appka nezbiera žiadne dáta – všetko ostáva v telefóne).
- **Age Rating** → vyplň dotazník, výsledok bude **4+**.
- **Pricing** → Free.

Nakoniec **Add for Review → Submit**. Schvaľovanie zvyčajne trvá 1–3 dni.

---

## ⚠️ Dôležité – aby appku neodmietli (Guideline 4.2)

Apple občas odmieta appky, ktoré sú „len obalený web bez pridanej hodnoty“.
Táto appka má reálnu funkčnosť (funguje offline, ukladá šatník, generuje
kombinácie), takže má dobrú šancu prejsť. Pre istotu:

- V popise zdôrazni, že appka **funguje offline** a dáta sú **lokálne v telefóne**.
- Pridaj pekné screenshoty so skutočným obsahom (nie prázdny šatník).
- Ak ju aj tak odmietnu s odkazom na 4.2, do *Resolution Center* napíš,
  že appka funguje plne offline a poskytuje natívnu hodnotu (správa šatníka,
  generovanie outfitov, obľúbené) – často to stačí.

---

## 7) (Voliteľné) TestFlight pred ostrým vydaním

Pred verejným vydaním môžeš build poslať sebe/známym cez **TestFlight**
(v App Store Connect záložka *TestFlight*) a appku si vyskúšať na reálnom iPhone.

---

## Lacnejšia alternatíva (zadarmo, bez App Store)

Ak appku chceš len pre seba a nemusí byť verejne v obchode:

1. Zapni **GitHub Pages** (Settings → Pages → Deploy from branch).
2. Na iPhone otvor adresu v **Safari** → tlačidlo **Zdieľať** →
   **Pridať na plochu**.

Appka sa pridá ako ikona na plochu, spúšťa sa na celú obrazovku a funguje
offline – bez 99 USD, bez Macu, bez schvaľovania. Je to ten istý kód, ktorý
by sa cez Capacitor balil aj do App Store.
