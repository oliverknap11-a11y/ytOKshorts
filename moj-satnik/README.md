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

## Ako to spustiť

Nepotrebuješ žiadnu inštaláciu ani server:

1. Stiahni si súbor `index.html` (alebo celý repozitár).
2. Otvor ho v prehliadači (dvojklik) – funguje na počítači aj v mobile.

Všetky dáta (fotky aj obľúbené outfity) sa ukladajú **len lokálne v tvojom
prehliadači** (localStorage) – nikam sa neposielajú. Fotky sa pri ukladaní
automaticky zmenšujú, aby sa zmestilo čo najviac kusov.

> Tip: ak chceš mať appku dostupnú z mobilu cez internet, stačí v nastaveniach
> repozitára zapnúť **GitHub Pages** (Settings → Pages → Deploy from branch → `main`).

## Technológie

Jediný súbor `index.html` – čisté HTML, CSS a JavaScript bez závislostí.
