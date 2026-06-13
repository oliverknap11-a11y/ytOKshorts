/**
 * Môj šatník – malý proxy pre AI funkcie. Drží API kľúče (secrets), appka volá toto.
 *
 * Podporuje dve akcie (pole "action" v JSON tele):
 *   - "tryon" (default): outfit oblečený na modelovi (virtual try-on)
 *   - "to3d": z viacerých fotiek kusu vyrobí 3D model (GLB)
 *
 * Voľba služby cez premenné:
 *   PROVIDER      = "mock" | "fashn"          (try-on)
 *   PROVIDER_3D   = "mock" | "tripo"          (image -> 3D)
 *
 * Try-on vstup:  { action:"tryon", model, top?, bottom?, dress? }  -> { image }
 * 3D vstup:      { action:"to3d", images:[<img>,...] }              -> { model: <glb url> }
 * <img> je URL alebo data URI.
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

    const action = (body.action || "tryon").toLowerCase();

    try {
      if (action === "to3d") {
        if (!Array.isArray(body.images) || !body.images.length)
          return json({ error: "Chýbajú fotky (images)." }, 400);
        const provider = (env.PROVIDER_3D || "mock").toLowerCase();
        const fn = TO3D[provider];
        if (!fn) return json({ error: "Neznámy PROVIDER_3D: " + provider }, 500);
        const model = await fn(body, env);
        return json({ model, provider });
      }

      // --- try-on ---
      if (!body.model) return json({ error: "Chýba 'model' (fotka osoby)." }, 400);
      if (!body.top && !body.bottom && !body.dress)
        return json({ error: "Chýba oblečenie (top/bottom/dress)." }, 400);
      const provider = (env.PROVIDER || "mock").toLowerCase();
      const fn = TRYON[provider];
      if (!fn) return json({ error: "Neznámy PROVIDER: " + provider }, 500);
      const image = await fn(body, env);
      return json({ image, provider });
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 502);
    }
  },
};

/* ============================ TRY-ON ============================ */

const TRYON = {
  // Ukážkový režim – bez kľúča, bez platby.
  async mock(b) {
    await new Promise((r) => setTimeout(r, 600));
    return b.dress || b.top || b.bottom || b.model;
  },

  // Reálny try-on cez FASHN.ai (over polia podľa https://docs.fashn.ai).
  async fashn(b, env) {
    if (!env.FASHN_API_KEY) throw new Error("Chýba secret FASHN_API_KEY.");
    const apply = (m, g, cat) => fashnRun(m, g, cat, env.FASHN_API_KEY);
    if (b.dress) return await apply(b.model, b.dress, "one-pieces");
    let cur = b.model;
    if (b.top) cur = await apply(cur, b.top, "tops");
    if (b.bottom) cur = await apply(cur, b.bottom, "bottoms");
    return cur;
  },
};

async function fashnRun(modelImage, garmentImage, category, key) {
  const start = await fetch("https://api.fashn.ai/v1/run", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({ model_name: "tryon-v1.5", inputs: { model_image: modelImage, garment_image: garmentImage, category } }),
  });
  if (!start.ok) throw new Error("FASHN run zlyhal: " + start.status + " " + (await start.text()));
  const { id } = await start.json();
  if (!id) throw new Error("FASHN nevrátil id.");
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const st = await fetch("https://api.fashn.ai/v1/status/" + id, { headers: { Authorization: "Bearer " + key } });
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

/* ============================ IMAGE -> 3D ============================ */

const TO3D = {
  // Ukážka – vráti reálny verejný GLB (kačička z Khronos sample assets),
  // aby sa dal otestovať 3D prehliadač v appke bez platby/kľúča.
  async mock() {
    await new Promise((r) => setTimeout(r, 800));
    return "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/Duck/glTF-Binary/Duck.glb";
  },

  // Reálne image -> 3D cez Tripo3D (over endpointy podľa https://platform.tripo3d.ai/docs).
  async tripo(b, env) {
    if (!env.TRIPO_API_KEY) throw new Error("Chýba secret TRIPO_API_KEY.");
    const headers = { "Content-Type": "application/json", Authorization: "Bearer " + env.TRIPO_API_KEY };
    const start = await fetch("https://api.tripo3d.ai/v2/openapi/task", {
      method: "POST",
      headers,
      body: JSON.stringify({ type: "multiview_to_model", files: b.images.map((url) => ({ type: "url", url })) }),
    });
    if (!start.ok) throw new Error("Tripo task zlyhal: " + start.status + " " + (await start.text()));
    const startData = await start.json();
    const taskId = startData && startData.data && startData.data.task_id;
    if (!taskId) throw new Error("Tripo nevrátil task_id.");
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const st = await fetch("https://api.tripo3d.ai/v2/openapi/task/" + taskId, { headers });
      const data = (await st.json()).data || {};
      if (data.status === "success") {
        const glb = data.output && (data.output.pbr_model || data.output.model);
        if (!glb) throw new Error("Tripo: prázdny výstup.");
        return glb;
      }
      if (data.status === "failed" || data.status === "banned") throw new Error("Tripo zlyhal.");
    }
    throw new Error("Tripo: vypršal čas (timeout).");
  },
};
