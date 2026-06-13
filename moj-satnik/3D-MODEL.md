# 3D model oblečenia (z viacerých fotiek)

Cieľ: z fotiek kusu (ideálne z viacerých uhlov) vyrobiť **otáčateľný 3D model**,
ktorý si v appke prezrieš.

> Úprimne: je to **veľká, samostatná fáza**. 3D rekonštrukcia oblečenia
> (photogrammetry / image-to-3D) je náročná – mäkká látka, záhyby a lesk robia
> výsledky nestabilné. Robíme to preto po krokoch a s reálnou službou až keď si
> vyberieš poskytovateľa.

## Ako to funguje

```
fotky kusu (1..N uhlov) → image-to-3D služba (cloud) → GLB súbor → 3D prehliadač v appke
```

- **GLB** je štandardný formát 3D modelu.
- Na zobrazenie používame webový komponent **`<model-viewer>`** (Google) –
  otáčanie prstom, automatické otáčanie, aj AR na podporovaných telefónoch.

## Čo je už hotové ✅

- **Proxy** (`tryon-proxy/`): nová akcia `to3d`. `PROVIDER_3D = "mock"` vráti
  **reálny ukážkový GLB** (otestuješ prehliadač zadarmo), pripravený adaptér
  **`tripo`** (Tripo3D, multiview → model). Pridať inú službu = jeden adaptér.
- **Appka**: pri každom kuse v šatníku je tlačidlo **„🧊 3D“**. Otvorí okno, kde
  vieš **pridať fotky z viacerých uhlov** a dať **„Vytvoriť 3D model“**. Appka
  zavolá proxy, uloží odkaz na model ku kusu a zobrazí **otáčateľný 3D model**.
  Tok appka → proxy → uložený model je **otestovaný** (v mock režime).

## Čo ešte treba (od teba)

1. **Vybrať image-to-3D službu** a získať **API kľúč** (porovnanie nižšie).
2. **Nasadiť proxy** (už máš návod v `tryon-proxy/README.md`):
   - kľúč ako secret, napr. `wrangler secret put TRIPO_API_KEY`
   - vo `wrangler.toml` `PROVIDER_3D = "tripo"`, potom `wrangler deploy`.

## Porovnanie služieb (image → 3D)

| Služba | Vstup | Pozn. |
|--------|-------|-------|
| **Tripo3D** | 1 alebo viac fotiek (multiview) | rýchle, slušná cena, jednoduché API (predvolený adaptér) |
| **Meshy** | 1 fotka / multiview | populárne, beží aj v prehliadači, kredity |
| **Luma / Genie** | fotky / video | dobrá kvalita, viac pre scény |
| **Rodin (Hyper3D)** | fotky | zamerané na objekty/postavy |

Ceny sú kreditové (per model) a u všetkých sa menia – over si aktuálny cenník.
Odporúčam začať **Tripo3D** (adaptér je pripravený).

## Dôležité (na rovinu)

- **Kvalita**: z 1 fotky vznikne hrubý model; pre slušný výsledok treba viac
  uhlov (predok/bok/zadok) a aj tak látka býva problém.
- **Internet**: 3D generovanie aj prehliadač (`model-viewer`) potrebujú
  pripojenie – to je v poriadku, lebo generovanie je aj tak online.
- **Súvislosť s try-on**: 2D virtual try-on (čo už máme) 3D model
  **nevyužíva** – pracuje s 2D fotkou. 3D je samostatná funkcia.
- **„AI model oblečie 3D outfit“** by bola ešte väčšia fáza (3D avatar +
  simulácia látky, úroveň CLO3D) – to je samostatný, veľký projekt.

## Fázy

1. **(hotové)** pipeline + 3D prehliadač + mock.
2. napojiť reálnu službu (Tripo3D) + tvoj kľúč → reálne 3D modely kusov.
3. (voliteľné, veľké) 3D obliekanie na 3D avatara so simuláciou látky.
