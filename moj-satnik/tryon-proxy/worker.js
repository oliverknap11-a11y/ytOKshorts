/**
 * Môj šatník – malý proxy pre AI virtual try-on.
 *
 * Appka volá tento Worker; API kľúč k AI službe je tu ako tajomstvo (secret),
 * takže sa nikdy nedostane do appky. Voľba služby je cez premennú PROVIDER.
 *
 *   PROVIDER = "mock"  -> nič neplatíš, vráti ukážkový obrázok (na test pipeline)
 *   PROVIDER = "fashn" -> reálny try-on cez FASHN.ai (treba secret FASHN_API_KEY)
 *
 * Vstup (POST JSON):
 *   { model: <img>, top?: <img>, bottom?: <img>, dress?: <img> }
 *   kde <img> je URL alebo data URI obrázka.
 * Výstup: { image: <url alebo data URI výsledku> }
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (req.method !== "POST") return json({ error: "Použi POST." }, 405);

    let body;
    try { body = await req.json(); }
    catch { return json({ error: "Neplatné JSON telo." }, 400); }

    if (!body.model) return json({ error: "Chýba 'model' (fotka osoby)." }, 400);
    if (!body.top && !body.bottom && !body.dress)
      return json({ error: "Chýba oblečenie (top/bottom/dress)." }, 400);

    const provider = (env.PROVIDER || "mock").toLowerCase();
    const fn = PROVIDERS[provider];
    if (!fn) return json({ error: "Neznámy PROVIDER: " + provider }, 500);

    try {
      const image = await fn(body, env);
      return json({ image, provider });
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 502);
    }
  },
};

const PROVIDERS = {
  // Ukážkový režim – bez kľúča, bez platby. Vráti vstupný obrázok,
  // aby sa dala vyskúšať celá cesta appka → proxy → výsledok.
  async mock(b) {
    await new Promise((r) => setTimeout(r, 600));
    return b.dress || b.top || b.bottom || b.model;
  },

  // Reálny try-on cez FASHN.ai. POZOR: presné názvy polí/endpointov si over
  // podľa aktuálnej dokumentácie https://docs.fashn.ai – sú izolované tu nižšie.
  async fashn(b, env) {
    if (!env.FASHN_API_KEY) throw new Error("Chýba secret FASHN_API_KEY.");
    const apply = (modelImg, garment, category) =>
      fashnRun(modelImg, garment, category, env.FASHN_API_KEY);

    if (b.dress) return await apply(b.model, b.dress, "one-pieces");

    let current = b.model;
    if (b.top) current = await apply(current, b.top, "tops");
    if (b.bottom) current = await apply(current, b.bottom, "bottoms");
    return current;
  },
};

async function fashnRun(modelImage, garmentImage, category, key) {
  const start = await fetch("https://api.fashn.ai/v1/run", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({
      model_name: "tryon-v1.5",
      inputs: { model_image: modelImage, garment_image: garmentImage, category },
    }),
  });
  if (!start.ok) throw new Error("FASHN run zlyhal: " + start.status + " " + (await start.text()));
  const { id } = await start.json();
  if (!id) throw new Error("FASHN nevrátil id.");

  // poll
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const st = await fetch("https://api.fashn.ai/v1/status/" + id, {
      headers: { Authorization: "Bearer " + key },
    });
    const data = await st.json();
    if (data.status === "completed") {
      const out = Array.isArray(data.output) ? data.output[0] : data.output;
      if (!out) throw new Error("FASHN: prázdny výstup.");
      return out;
    }
    if (data.status === "failed") throw new Error("FASHN zlyhal: " + (data.error || "neznáma chyba"));
  }
  throw new Error("FASHN: vypršal čas (timeout).");
}
