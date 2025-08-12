// tiktok_live.js — Captura métricas de un Live de TikTok y guarda en live_<usuario>.json
// Requisitos:  npm init -y && npm i tiktok-live-connector
// Ejecutar (PowerShell):
//   $env:TIKTOK_USERNAME="usuario_en_vivo"
//   # Opcional si TikTok bloquea: $env:TIKTOK_SESSION_ID="<sessionid>"; $env:TIKTOK_MS_TOKEN="<msToken>"
//   node .\tiktok_live.js
//
// También se puede pasar el usuario como argumento:  node tiktok_live.js usuario_en_vivo

const { WebcastPushConnection } = require("tiktok-live-connector");
const fs = require("fs");
const path = require("path");

// -------- Config --------
const USERNAME = (process.env.TIKTOK_USERNAME || process.argv[2] || "").trim().replace(/^@/, "");
if (!USERNAME) {
  console.error("❌ Debes indicar el usuario. Ej: $env:TIKTOK_USERNAME='usuario'  o  node tiktok_live.js usuario");
  process.exit(1);
}

// Si TIKTOK_JSON_PATH no está, guardamos en live_<usuario>.json en el cwd
const OUT_JSON = process.env.TIKTOK_JSON_PATH || path.resolve(process.cwd(), `live_${USERNAME}.json`);

// Cookies/UA para evitar bloqueos regionales
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
const headers = { "User-Agent": UA };
const cookieParts = [];
if (process.env.TIKTOK_SESSION_ID) cookieParts.push(`sessionid=${process.env.TIKTOK_SESSION_ID}`);
if (process.env.TIKTOK_MS_TOKEN)   cookieParts.push(`msToken=${process.env.TIKTOK_MS_TOKEN}`);
if (cookieParts.length) headers.Cookie = cookieParts.join("; ");

const conn = new WebcastPushConnection(USERNAME, { requestOptions: { headers } });

// -------- Estado --------
const state = {
  username: USERNAME,
  likes: 0,
  comments: 0,
  viewers: 0,
  diamonds: 0,
  shares: 0,
  gifts: [], // { user, gift, amount, diamonds, ts }
  startedAt: new Date().toISOString(),
  lastUpdate: null,
};

// Guardado con debounce
let t = null;
function scheduleSave() {
  if (t) clearTimeout(t);
  t = setTimeout(saveNow, 300);
}
function saveNow() {
  try {
    state.lastUpdate = new Date().toISOString();
    fs.writeFileSync(OUT_JSON, JSON.stringify(state, null, 2), { encoding: "utf-8" });
  } catch (e) {
    console.error("❌ Error escribiendo JSON:", e.message);
  }
}

// -------- Eventos --------
conn.on("roomUser", (d) => {
  if (typeof d.viewerCount === "number") state.viewers = d.viewerCount;
  scheduleSave();
});

conn.on("like", (d) => {
  if (typeof d.likeCount === "number") state.likes += d.likeCount;
  else if (typeof d.totalLikeCount === "number") state.likes = d.totalLikeCount;
  scheduleSave();
});

conn.on("chat", () => {
  state.comments += 1;
  scheduleSave();
});

const onShare = () => { state.shares += 1; scheduleSave(); };
conn.on("share", onShare);
conn.on("social", (ev) => {
  if (ev && (ev.displayType === "share" || ev.label === "share")) onShare();
});

conn.on("gift", (d) => {
  const item = {
    user: d.uniqueId,
    gift: d.giftName,
    amount: d.repeatCount || 1,
    diamonds: d.diamondCount || 0,
    ts: new Date().toISOString(),
  };
  state.gifts.push(item);
  state.diamonds += item.diamonds;
  scheduleSave();
});

conn.on("disconnected", () => {
  console.warn("⚠️  Desconectado. Reintentando en 2s...");
  setTimeout(connect, 2000);
});

conn.on("streamEnd", () => {
  console.warn("🛑 El stream terminó.");
  scheduleSave();
});

async function connect() {
  try {
    const info = await conn.connect();
    console.log(`✅ Conectado a @${USERNAME} | RoomId: ${info.roomId}`);
    console.log(`Guardando en: ${OUT_JSON}`);
  } catch (err) {
    console.error("❌ Error conectando:", err?.message || err);
    if ((err?.message || "").includes("SIGI_STATE")) {
      console.error("Sugerencia: agrega $env:TIKTOK_SESSION_ID y (opcional) $env:TIKTOK_MS_TOKEN");
    }
    console.error("Reintentando en 5s...");
    setTimeout(connect, 5000);
  }
}

connect();

process.on("SIGINT", () => { console.log("\n💾 Guardando y saliendo..."); try { saveNow(); } catch {} process.exit(0); });
process.on("SIGTERM", () => { console.log("\n💾 Guardando y saliendo..."); try { saveNow(); } catch {} process.exit(0); });
