# Try-on proxy (Cloudflare Worker)

Malý server, ktorý drží API kľúč k AI try-on službe a appka volá jeho.
Vďaka nemu sa kľúč nikdy nedostane do appky a nie sú problémy s CORS.

## Prečo to potrebuješ

AI „obliekanie“ outfitov na model beží v cloude a platí sa zaň. Kľúč k tejto
službe nesmie byť priamo v appke (ktokoľvek by ho videl). Preto ho dáme do
tohto Workera ako tajomstvo a appka volá iba Worker.

## Nasadenie (zdarma, Cloudflare)

1. Vytvor si účet na https://dash.cloudflare.com (zadarmo).
2. Nainštaluj nástroj a prihlás sa:
   ```bash
   npm install -g wrangler
   wrangler login
   ```
3. V tomto priečinku nasaď Worker:
   ```bash
   wrangler deploy
   ```
   Dostaneš adresu typu `https://satnik-tryon-proxy.<účet>.workers.dev`.
   **Túto adresu vložíš v appke** do sekcie „AI skúšobňa“.

## Voľba služby

- Predvolene je `PROVIDER = "mock"` (vo `wrangler.toml`) – funguje **hneď,
  zadarmo**, vráti ukážkový obrázok. Slúži na otestovanie, že appka ↔ proxy
  funguje.
- Keď si vyberieš reálnu službu (odporúčam **FASHN.ai**):
  1. Získaj API kľúč na https://fashn.ai.
  2. Ulož ho ako tajomstvo:
     ```bash
     wrangler secret put FASHN_API_KEY
     ```
  3. V `wrangler.toml` zmeň `PROVIDER = "fashn"` a znova `wrangler deploy`.

> Adaptér pre FASHN je vo `worker.js` v jednej funkcii (`fashnRun`). Ak by sa
> zmenili názvy polí v ich API, upraví sa len tam. Pridať inú službu
> (Replicate, Kling…) = pridať jeden adaptér do objektu `PROVIDERS`.

## Test z príkazového riadku

```bash
curl -X POST https://<tvoj-worker>.workers.dev \
  -H "Content-Type: application/json" \
  -d '{"model":"https://.../osoba.jpg","top":"https://.../tricko.jpg","bottom":"https://.../nohavice.jpg"}'
```

Vráti `{ "image": "...", "provider": "mock" }`.
