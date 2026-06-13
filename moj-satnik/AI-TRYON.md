# AI skúšobňa – outfit oblečený na modelovi (plán)

Cieľ: namiesto (alebo popri) dvoch fotiek nad sebou ukázať **jednu fotku
modela/modelky, ktorá má daný outfit reálne oblečený**. Toto je tzv.
**virtual try-on** a robí to generatívna AI.

## Krátka odpoveď: áno, treba API kľúč k externej AI

Takéto fotky **nevie appka vyrobiť lokálne/offline** – generovanie obrazu beží
na výkonných modeloch v cloude. Potrebuješ účet + **API kľúč** k niektorej
try-on službe a platí sa za vygenerovaný obrázok. Bez internetu a kľúča to
nefunguje.

> Dôležité: dnes je appka 100 % offline a súkromná. Try-on je **online funkcia** –
> fotky oblečenia (a prípadne tvoja fotka) sa pošlú do zvolenej AI služby.
> Preto to navrhujem ako **voliteľnú funkciu**, ktorú si zapneš sám, a do
> popisu/súkromia doplníme jasnú informáciu.

## Ako to technicky funguje

Vstup: **fotka osoby (model)** + **fotka kusu oblečenia** → výstup: osoba
oblečená v tom kuse.

Náš outfit je ale **vrchný + spodný diel (2 kusy)**. Väčšina modelov oblieka
jeden kus naraz, takže to **zreťazíme**:

```
model → (obleč vrchný diel) → medzivýsledok → (obleč spodný diel) → finál
šaty  → (obleč ako "one-piece") → finál (1 krok)
```

To znamená ~2 volania API na jeden outfit (1 pri šatách).

## „Kto je ten model?“ – tri možnosti

1. **Tvoja vlastná fotka** (selfie / postava) – najosobnejšie, vidíš seba.
2. **Pripravené AI modely** – appka ponúkne pár postáv na výber.
3. **Vygenerovaný model** – z textu (typ postavy) cez image AI.

Odporúčam kombináciu **1 + 2** (zopár prednastavených + možnosť nahrať seba).

## Porovnanie služieb (stav 2026)

| Služba | Cena (orientačne) | Plus | Mínus |
|--------|-------------------|------|-------|
| **FASHN.ai** | ~$0.075 / obrázok (menej pri objeme), 4K od $19/mes | špecializované na módu, vie vrchný/spodný/šaty, presné vzory | platené per obrázok |
| **fal.ai** (hostuje FASHN v1.5) | per obrázok, podľa modelu | jednoduché API, podpora aj z prehliadača (cez proxy) | tiež platené |
| **Replicate** (IDM-VTON, CatVTON, OOTDiffusion) | platba za sekundy behu | lacné pri malom objeme, výber modelov | kvalita kolíše, treba ladiť |
| **Kling / Kolors Virtual Try-On** | per obrázok | dobrá kvalita | jeden zdieľaný model |
| **Google Vertex AI Virtual Try-On** | podľa GCP | enterprise, stabilné | zložitejšie nastavenie (GCP projekt) |

**Odporúčanie pre štart:** **FASHN.ai** (priamo alebo cez fal.ai) – je
najlacnejšie na obrázok, robené priamo pre módu a vie rozlíšiť vrchný/spodný
diel aj šaty.

## Architektúra – dve cesty

### A) Rýchlo (kľúč priamo v appke)
- Kľúč si uložíš v appke (lokálne), appka volá API priamo z WebView.
- ✅ žiadny server, hneď použiteľné.
- ⚠️ kľúč je „v telefóne“ – pre osobné použitie ok; niektoré API to ale cez
  prehliadač blokujú (CORS) a kľúč by nemal ísť do verejnej appky.

### B) Správne (malý proxy server) — odporúčané ak pôjde appka von
- Malá serverless funkcia (napr. Cloudflare Worker / Vercel) drží kľúč u seba,
  appka volá ju, ona volá AI.
- ✅ kľúč je v bezpečí, žiadne CORS problémy, dá sa pridať limit/účtovanie.
- ⚠️ treba nasadiť jednu malú funkciu (spravím ti ju).

## Čo to spraví v appke (návrh UX)

- Pri každom outfite a pri „Outfit dňa“ pribudne tlačidlo **„Obleč na modela ✨“**.
- V nastaveniach: výber služby + API kľúč + výber/upload modela.
- Po kliknutí: indikátor „generujem…“, potom fotka modela v outfite, možnosť
  **uložiť / zdieľať** a označiť ❤.
- Výsledky sa kešujú (rovnaký outfit + model = negeneruje sa znova = šetrí kredit).

## Čo je už hotové ✅

Podľa tvojich rozhodnutí (službu vyberieme neskôr, prednastavené modely, proxy
server) je už postavené:

- **Proxy server** – `tryon-proxy/` (Cloudflare Worker) s voľbou služby cez
  premennú `PROVIDER`. Má režim **`mock`** (funguje hneď, zadarmo) a pripravený
  adaptér **`fashn`** (FASHN.ai). Pridať inú službu = jeden adaptér navyše.
- **Appka** – sekcia „AI skúšobňa“ (adresa proxy + výber prednastaveného modela)
  a tlačidlo **„🧍 Obleč na modela“** pri každom outfite aj pri Outfit dňa.
  Volá proxy, zobrazí výsledok, vie ho uložiť, a kešuje (nešetrí kredit zbytočne).
  Otestované end-to-end v `mock` režime.

## Čo ešte treba (od teba)

1. **Vybrať AI službu** (odporúčam FASHN.ai) a získať k nej **API kľúč**.
2. **Nasadiť proxy** podľa `tryon-proxy/README.md`, vložiť kľúč ako secret,
   prepnúť `PROVIDER` na zvolenú službu.
3. **Reálne fotky modelov** – prednastavené modely sú teraz placeholder siluety;
   nahradia sa reálnymi/AI vygenerovanými fotkami osôb (vie ich vygenerovať aj
   FASHN). Doplníme po výbere služby.
