# Môj šatník – mobilná appka (Expo)

Mobilný (iOS/Android) obal pre webovú appku `../index.html`, postavený na
**Expo**. Appka beží vo `WebView`, takže používa presne tú istú appku ako web,
ale dá sa publikovať do App Store / Google Play.

**Hlavná výhoda:** appku do App Store vieš zostaviť a nahrať **bez Macu** –
cez cloud službu **EAS Build** / **EAS Submit**. Návod: [`EAS-BUILD.md`](EAS-BUILD.md).

## Rýchly štart

```bash
npm install            # závislosti
npm run build:html     # zabalí ../index.html do assets/app-html.js
npx expo start         # spustí dev server (otvor v Expo Go alebo simulátore)
```

Build a publikovanie do App Store: pozri **[`EAS-BUILD.md`](EAS-BUILD.md)**.

## Ako to funguje

| Súbor | Načo je |
|-------|---------|
| `App.js` | natívny obal – `WebView`, ktorý načíta zabalenú appku |
| `assets/app-html.js` | **vygenerovaná** webová appka (z `../index.html`) |
| `scripts/build-html.mjs` | generátor `app-html.js` (`npm run build:html`) |
| `app.json` | konfigurácia Expo: názov *Môj šatník*, ikony, splash, bundle ID `com.mojsatnik.app` |
| `eas.json` | profily pre cloud build (EAS) |
| `assets/icon.png`, `splash-icon.png`, `adaptive-icon.png` | ikony a splash (z `../icons`) |
| `EAS-BUILD.md` | **návod na publikovanie bez Macu** |

## Dôležité

- Po každej zmene webovej appky (`../index.html`) spusti `npm run build:html`,
  inak sa zmena do mobilnej appky nedostane.
- Šatník sa v appke ukladá lokálne (localStorage WebView) a pretrváva medzi
  spusteniami – appka má kvôli tomu stabilnú internú adresu (`baseUrl` v `App.js`).
- `node_modules/`, `.expo/`, `ios/`, `android/` sa do gitu neukladajú.
- Texty pre obchod: [`../store-listing.md`](../store-listing.md),
  súkromie: [`../PRIVACY.md`](../PRIVACY.md).
