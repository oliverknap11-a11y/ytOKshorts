# Môj šatník – iOS (Capacitor)

Natívny iOS obal pre webovú appku `../index.html`. Webová appka je jediný
zdroj pravdy – tento priečinok ju len zabalí do natívnej iOS appky pre App Store.

## Rýchly štart (na Macu)

```bash
npm install          # Capacitor a nástroje
npm run ios:add      # skopíruje appku do www/ a vytvorí iOS projekt
npm run ios:assets   # vygeneruje ikony + splash z ../icons/icon-1024.png
npm run ios:open     # otvorí projekt v Xcode
```

Po každej zmene webovej appky:

```bash
npm run ios:sync
```

## Súbory

| Súbor | Načo je |
|-------|---------|
| `capacitor.config.json` | appId `com.mojsatnik.app`, názov, webDir |
| `scripts/sync-web.mjs` | skopíruje `../index.html`, manifest, SW a ikony do `www/` |
| `APP-STORE.md` | **kompletný návod na publikovanie do App Store (slovensky)** |
| `store-listing.md` | hotové texty a metadáta pre App Store Connect |
| `PRIVACY.md` | zásady ochrany súkromia (SK + EN) |

## Poznámky

- `www/`, `ios/` a `node_modules/` sa do gitu **neukladajú** – vznikajú lokálne
  pri builde (`www/` cez `sync:web`, `ios/` cez `cap add ios` na Macu).
- Natívny iOS projekt sa dá vytvoriť a buildovať **iba na macOS** s Xcode 16+ –
  je to požiadavka Apple.
- Potrebuješ Node 20+, CocoaPods a (na publikovanie) Apple Developer účet.
