// v3.64 Cloudflare Worker: FULL Telegram Control for Viral Gyaan Cloud VideoTool (24/7, $0/mo)
// Features:
//  - Persistent Menu Keyboard (Aaj shuru karo, Long Prompt, Status, /rok, /log, /purana, /guide)
//  - Instant 5-Shorts Micro-Beat Master Prompt & Long News+Fact Documentary Prompt
//  - REAL /rok -> cancels any active/queued GitHub Actions cloud render in 1 second!
//  - Live /status & /log -> shows live cloud job status & clickable GitHub log link!
//  - ZIP + caption "update" -> auto-updates your GitHub Cloud repo in 30s!
//  - /purana -> rolls back last cloud update!

const KEYBOARD = {
  keyboard: [
    [{ text: "▶️ Aaj shuru karo (5 Prompt)" }, { text: "🎬 Long Prompt" }],
    [{ text: "📊 /status" }, { text: "🛑 /rok" }, { text: "📜 /log" }],
    [{ text: "⏪ /purana" }, { text: "📖 /guide" }],
  ],
  resize_keyboard: true,
  is_persistent: true,
};

const SHORTS_PROMPT = `MERA TOPIC (1 se 5 topic likho, ya "AUTO" rehne do to 5 viral topics khud aayenge):
<<< AUTO >>>

You are India's #1 viral Hindi YouTube Shorts scriptwriter for "The Viral Gyaan" (science, space, ocean, mystery, world news facts, history, tech).
My automated VideoTool reads every line and picks visuals STRICTLY from the English hint after "||".
Write 5 complete Hindi Shorts scripts separated by a line with only ====

STRICT MICRO-BEAT RULES (40-55 sec, 14-18 SHORT lines per script, 5-9 words per line — ONE single visual idea/emotion per line!):
0. NEVER mix 2 contrasting ideas in 1 line! Split them into 2 short lines so each emotion/object gets its OWN exact visual (e.g. Line A: "इसके पीछे पैसे की कमी नहीं है।" || stacks of cash money closeup -> Line B: "बल्कि प्रकृति की अजीब ताकत है।" || violent storm waves crashing ocean).
1. HOOK (Line 1): Shocking/curious hook in first 2s. NEVER start with "दोस्तों" or "क्या आप जानते हैं".
2. Include 1 real big number with unit (e.g. 6400 किलोमीटर / 90%) and 1 real year/report line (e.g. साल 2011 में).
3. Include 1 twist line ("लेकिन चौंकाने वाली बात यह है...").
4. Last line CTA (NO "||" on last line): ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।

VISUAL HINT RULES (EVERY LINE EXCEPT LAST CTA MUST HAVE "||"):
- REAL STOCK (75% lines): || <3-5 concrete filmable English words: object + action + shot> (e.g. "deep ocean waves aerial view", "wooden boat crossing wide river", "scientist laboratory microscope closeup"). NO abstract words ("secret", "shocking", "mystery"), NO text/logos.
- IMPOSSIBLE / CUSTOM AI SCENE (2-4 lines): || AI: <8-14 vivid realistic documentary words> (e.g. "AI: sunken rusted satellite on dark deep ocean floor dramatic underwater light rays").
- Optional [map: Place, Country] at end of 1 geography line right BEFORE "||".
- NO emojis, NO hashtags, NO bold (**), NO numbering, NO extra notes.

OUTPUT EXACTLY:
TITLE: <2-4 crisp words> | <2-4 hook words>
<line 1> || <visual hint>
...
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।
====
TITLE: <Script 2> | <hook>
...`;

const LONG_PROMPT = `MERA TOPIC (Long News + Fact Documentary Video):
<<< yahan apna topic ya breaking news + fact likho >>>

You are India's #1 Hindi Long-Form News & Fact Documentary scriptwriter (Dhruv Rathee / Nitish Rajput style) for "The Viral Gyaan".
Write a 3-6 min documentary script (28-45 lines, 10-16 words per line) divided into 3-5 chapters using "## Chapter Name":
- ## शुरुआत (Strong hook + why it matters today)
- ## असली कहानी (Timeline, real years & official report/court/survey facts)
- ## चौंकाने वाले आंकड़े (Key numbers, %, crore/km stats)
- ## बड़ा असर और निष्कर्ष (Takeaway + clean subscribe CTA)

VISUAL HINTS (EVERY LINE EXCEPT LAST CTA LINE MUST HAVE "||"):
- REAL STOCK (75%): || <3-5 concrete filmable English words>
- CUSTOM AI SCENE (25%): || AI: <8-14 vivid realistic documentary words>
- Put [map: Place, Country] on 1-2 geography lines before "||".
- Include real years and words like "रिपोर्ट", "सर्वे", "सरकार", "अदालत", "रिसर्च" on proof lines!
- NO emojis, NO hashtags, NO bold (**), NO numbering.

OUTPUT EXACTLY:
LONG
TITLE: <documentary title> | <hook subtitle>
## शुरुआत
<line 1> || <visual hint>
...
ऐसे ही गहरे रिसर्च वाले न्यूज़ और फैक्ट वीडियो के लिए चैनल को सब्सक्राइब ज़रूर करें।`;

const GUIDE_TEXT = `📖 VIRAL GYAAN CLOUD BOT (24×7)

• ▶️ Aaj shuru karo (5 Prompt): ChatGPT/Gemini ke liye 5 Shorts ka micro-beat prompt milta hai.
• 🎬 Long Prompt: News + Fact documentary (16:9) ka prompt milta hai.
• Script bhejna: Seedha apni script paste karke bhejo (Long ke liye sabse upar LONG likho).
• 🛑 /rok: Cloud par chal rahi video ko turant rokta hai.
• 📊 /status aur 📜 /log: Live progress aur GitHub log link dikhata hai.
• 📦 Update: Koi bhi nayi .zip file caption "update" ke saath bhejo -> cloud 30 sec me update!
• ⏪ /purana: Pichhle version par wapas jaane ke liye.`;

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("VideoTool Cloud Bridge v3.64 is LIVE!", { status: 200 });
    }
    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("ok", { status: 200 });
    }
    // v3.79: buttons (Short / Long / meri awaaz) ka jawab
    if (update.callback_query) {
      await handleChoice(env, update.callback_query);
      return new Response("ok", { status: 200 });
    }
    const msg = update.message || update.edited_message;
    if (!msg) return new Response("ok", { status: 200 });

    const chatId = String(msg.chat.id);
    if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) {
      return new Response("ok", { status: 200 });
    }

    // 1) Telegram ZIP auto-update (caption: update)
    const doc = msg.document;
    const cap = (msg.caption || "").trim().toLowerCase();
    const fnLo = (doc && doc.file_name ? doc.file_name.toLowerCase() : "");
    if (doc && fnLo.endsWith(".zip") && (cap.includes("update") || fnLo.startsWith("vg_"))) {
      const ok = await dispatchGH(env, "apply_update.yml", { action: "update", file_id: doc.file_id });
      await tgReply(env.TG_TOKEN, chatId, ok
        ? "📦 Update ZIP mil gayi! Cloud par compile aur install kar raha hoon (~40 sec)..."
        : "❌ GitHub update trigger fail. GH_TOKEN permissions (Contents + Actions: Read & Write) check karo.");
      return new Response("ok", { status: 200 });
    }

    // 1b) v3.69: cookies.txt (YouTube / X) phone se -> sirf file_id repo me (cookies khud repo me NAHI jaati)
    if (doc && (fnLo.endsWith(".txt") || fnLo.endsWith(".json")) && (fnLo.includes("cookie") || cap.includes("cookie"))) {
      const both = fnLo + " " + cap;
      const kind = (both.includes("x.com") || both.includes("twitter") || /(^|[^a-z])x([^a-z]|$)/.test(cap)) ? "x" : "youtube";
      const ok = await saveCookieRef(env, kind, doc.file_id);
      await tgReply(env.TG_TOKEN, chatId, ok
        ? `🍪 ${kind === "x" ? "X/Twitter" : "YouTube"} cookies mil gayi ✓ Agli video se apne aap lagengi.\n` +
          "Is message ko DELETE mat karna. Jaanch ke liye: SYSTEM JAANCH KARO"
        : "❌ Cookies save nahi hui – GH_TOKEN ko Contents: Read and write permission chahiye.", true);
      return new Response("ok", { status: 200 });
    }

    // v3.79: aapki awaaz (voice note / audio file) -> pehle chuni hui script ke saath video
    const aud = msg.voice || msg.audio || (doc && /^(audio|video)\//.test(doc.mime_type || "") ? doc : null);
    if (aud && update.message) {
      const pend = await readPending(env);
      if (!pend || !pend.script || Date.now() - (pend.ts || 0) > 6 * 3600e3) {
        await tgReply(env.TG_TOKEN, chatId, "🎙 Awaaz mil gayi, par koi script intezaar me nahi hai.\nPehle script bhejo -> '🎙 meri awaaz' button dabao -> phir awaaz bhejo.", true);
        return new Response("ok", { status: 200 });
      }
      if ((aud.file_size || 0) > 20 * 1024 * 1024) {
        await tgReply(env.TG_TOKEN, chatId, "❌ Awaaz ki file 20 MB se badi hai (Telegram bot limit). Voice note ya chhoti mp3/m4a bhejo.", true);
        return new Response("ok", { status: 200 });
      }
      const sc = `VOICE_FILE_ID: ${aud.file_id}\n` + pend.script;
      const ok = await dispatchGH(env, "make_video.yml", { script: sc, mode: pend.mode === "L" ? "LONG" : "SHORT" });
      await clearPending(env);
      await tgReply(env.TG_TOKEN, chatId, ok
        ? `🚀 Aapki AWAAZ ke saath ${pend.mode === "L" ? "LONG" : "SHORT"} video shuru ho gayi!\nBante hi download link + video yahin aayegi.`
        : "❌ GitHub render trigger fail ho gaya.", true);
      return new Response("ok", { status: 200 });
    }

    const text = (msg.text || "").trim();
    const tl = text.toLowerCase();
    if (!text) return new Response("ok", { status: 200 });

    // 2) Start / Menu / Guide
    if (tl === "/start" || tl === "/menu") {
      await tgReply(env.TG_TOKEN, chatId,
        "☁️ VideoTool Cloud v3.64 LIVE hai!\nNeeche ke buttons use karo ya seedha script bhejo:", true);
      return new Response("ok", { status: 200 });
    }
    if (tl === "/guide" || text.includes("/guide")) {
      await tgReply(env.TG_TOKEN, chatId, GUIDE_TEXT, true);
      return new Response("ok", { status: 200 });
    }

    // 3) 5-Shorts Master Prompt & Long Documentary Prompt
    if (tl === "/aaj" || tl === "prompt" || tl === "प्रॉम्प्ट" || text.includes("Aaj shuru karo")) {
      await tgReply(env.TG_TOKEN, chatId,
        "📝 Neeche wala 5-Shorts Master Prompt COPY karo → ChatGPT ya Gemini me paste karo → jo script mile use yahan bhej do:", true);
      await tgReply(env.TG_TOKEN, chatId, SHORTS_PROMPT, false);
      return new Response("ok", { status: 200 });
    }
    if (tl === "/aaj long" || tl === "long prompt" || tl === "लॉन्ग प्रॉम्प्ट" || text.includes("Long Prompt")) {
      await tgReply(env.TG_TOKEN, chatId,
        "🎬 Neeche wala Long News+Fact Prompt COPY karo → ChatGPT ya Gemini me paste karo → jawab yahan bhej do:", true);
      await tgReply(env.TG_TOKEN, chatId, LONG_PROMPT, false);
      return new Response("ok", { status: 200 });
    }

    // 4) REAL /rok -> Cancel running & queued GitHub Actions jobs!
    if (tl === "/rok" || text.includes("/rok") || tl === "rok" || tl === "stop") {
      const canceled = await cancelActiveRuns(env);
      await tgReply(env.TG_TOKEN, chatId, canceled > 0
        ? `🛑 ${canceled} chal rahi cloud video rok (cancel) di gayi hai!`
        : "ℹ️ Abhi cloud par koi video nahi chal rahi hai.", true);
      return new Response("ok", { status: 200 });
    }

    // 5) Live /status & /log from GitHub Actions API
    if (tl === "/status" || text.includes("/status") || tl === "/log" || text.includes("/log")) {
      const summary = await getRunsSummary(env);
      await tgReply(env.TG_TOKEN, chatId, summary, true);
      return new Response("ok", { status: 200 });
    }

    // 6) Rollback /purana
    if (tl === "/purana" || text.includes("/purana")) {
      const ok = await dispatchGH(env, "apply_update.yml", { action: "rollback", file_id: "" });
      await tgReply(env.TG_TOKEN, chatId, ok
        ? "⏪ Pichhla version (/purana) cloud par restore kar raha hoon (~30 sec)..."
        : "❌ Rollback trigger fail ho gaya.", true);
      return new Response("ok", { status: 200 });
    }

    if (text.length < 15) {
      await tgReply(env.TG_TOKEN, chatId, "⚠️ Script bahut chhoti hai. Poori script bhejo ya neeche ka button dabao!", true);
      return new Response("ok", { status: 200 });
    }

    // 6b) v3.79: script aayi -> pehle poochho: Short / Long / meri awaaz (pehle seedha Short ban jaati thi)
    const firstUp = text.split("\n")[0].trim().toUpperCase();
    const explicit = /^(LONG|LAMBI|SHORT|SHORTS)\b/.test(firstUp) || /^(SYSTEM JAANCH|YTDLP JAANCH|SYSTEM CHECK)/.test(firstUp);
    if (!explicit && update.message) {
      await askChoice(env, chatId, msg.message_id, text);
      return new Response("ok", { status: 200 });
    }

    // 7) Multi-script (====) or Single Script Render!
    const parts = text.split(/\n\s*={3,}\s*\n/).map(s => s.trim()).filter(s => s.length >= 25);
    const scripts = parts.length >= 2 ? parts : [text];
    let launched = 0;
    for (const sc of scripts) {
      const isLong = sc.toUpperCase().startsWith("LONG");
      const ok = await dispatchGH(env, "make_video.yml", { script: sc, mode: isLong ? "LONG" : "SHORT" });
      if (ok) launched++;
    }
    await tgReply(env.TG_TOKEN, chatId, launched > 0
      ? `🚀 ${launched} video cloud par shuru ho gayi hai!\nBante hi pehle Telegram aur 5 TB Google Drive par aayegi.\nStatus dekhne ke liye 📊 /status aur rokne ke liye 🛑 /rok dabao.`
      : "❌ GitHub render trigger fail ho gaya. GH_TOKEN aur GH_REPO check karo.", true);
    return new Response("ok", { status: 200 });
  },
};

async function ghFetch(env, path, method = "GET", body = null) {
  const opts = {
    method,
    headers: {
      "Authorization": `Bearer ${env.GH_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "VideoTool-Cloud-Worker",
      "Content-Type": "application/json",
    },
  };
  if (body) opts.body = JSON.stringify(body);
  return fetch(`https://api.github.com/repos/${env.GH_REPO}${path}`, opts);
}

// ---------------- v3.79: Short / Long / meri awaaz chunav ----------------
const CHOICE_KB = {
  inline_keyboard: [
    [{ text: "📱 Short", callback_data: "mk:S" }, { text: "📺 Long video", callback_data: "mk:L" }],
    [{ text: "🎙 Short + meri awaaz", callback_data: "mv:S" }, { text: "🎙 Long + meri awaaz", callback_data: "mv:L" }],
    [{ text: "❌ Cancel", callback_data: "mk:X" }],
  ],
};

async function tgApi(env, method, payload) {
  return fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${method}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

async function askChoice(env, chatId, replyTo, text) {
  const n = text.split(/\n\s*={3,}\s*\n/).filter(s => s.trim().length >= 25).length;
  await tgApi(env, "sendMessage", {
    chat_id: chatId, reply_to_message_id: replyTo,
    text: `🎬 Script mil gayi${n >= 2 ? ` (${n} scripts)` : ""}! Kaunsi video banaun?`,
    reply_markup: CHOICE_KB,
  });
}

function splitScripts(text) {
  const parts = text.split(/\n\s*={3,}\s*\n/).map(s => s.trim()).filter(s => s.length >= 25);
  return parts.length >= 2 ? parts : [text];
}

async function handleChoice(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const data = cq.data || "";
  const orig = (cq.message.reply_to_message && (cq.message.reply_to_message.text || "")) || "";
  const edit = (t) => tgApi(env, "editMessageText", { chat_id: chatId, message_id: cq.message.message_id, text: t });
  if (data === "mk:X") { await edit("❌ Cancel – koi video nahi banegi."); return; }
  if (!orig.trim()) { await edit("⚠️ Script nahi mili (purana message). Script dobara bhejo."); return; }
  const mode = data.endsWith(":L") ? "L" : "S";
  if (data.startsWith("mv:")) {
    const ok = await savePending(env, { script: orig, mode, ts: Date.now() });
    await edit(ok
      ? `🎙 ${mode === "L" ? "LONG" : "SHORT"} + aapki awaaz.\nAb POORI script padh ke apni awaaz bhejo (voice note ya mp3/m4a file, 20 MB tak).\nShaant jagah, saaf awaaz – lines ki timing isi se banegi.`
      : "❌ Script save nahi hui – GH_TOKEN ko Contents: Read and write chahiye.");
    return;
  }
  let launched = 0;
  for (const sc of splitScripts(orig)) {
    const ok = await dispatchGH(env, "make_video.yml", { script: sc, mode: mode === "L" ? "LONG" : "SHORT" });
    if (ok) launched++;
  }
  await edit(launched > 0
    ? `🚀 ${launched} ${mode === "L" ? "LONG" : "SHORT"} video cloud par shuru!\nBante hi download link + video yahin aayegi. /status se haal dekho, /rok se roko.`
    : "❌ GitHub render trigger fail ho gaya. GH_TOKEN aur GH_REPO check karo.");
}

function b64e(str) {
  const bytes = new TextEncoder().encode(str); let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}
function b64d(b) {
  const bin = atob((b || "").replace(/\n/g, "")); const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

const PENDING = "/contents/seekha/pending_voice.json";
async function readPending(env) {
  try {
    const g = await ghFetch(env, PENDING);
    if (!g.ok) return null;
    const j = await g.json();
    const d = JSON.parse(b64d(j.content) || "{}");
    d._sha = j.sha; return d;
  } catch (e) { return null; }
}
async function savePending(env, obj) {
  const cur = await readPending(env);
  const body = { message: "pending voice script", content: b64e(JSON.stringify(obj)), branch: "main" };
  if (cur && cur._sha) body.sha = cur._sha;
  const r = await ghFetch(env, PENDING, "PUT", body);
  return r.ok;
}
async function clearPending(env) {
  const cur = await readPending(env);
  if (!cur || !cur._sha) return;
  await ghFetch(env, PENDING, "PUT", { message: "pending voice used", content: b64e("{}"), sha: cur._sha, branch: "main" });
}

async function saveCookieRef(env, kind, fileId) {
  // v3.69: seekha/cookies_ref.json me sirf Telegram file_id + date (bot token ke bina bekaar)
  const path = "/contents/seekha/cookies_ref.json";
  let sha = undefined, data = {};
  try {
    const g = await ghFetch(env, path);
    if (g.ok) {
      const j = await g.json();
      sha = j.sha;
      data = JSON.parse(atob((j.content || "").replace(/\n/g, "")) || "{}");
    }
  } catch (e) { data = {}; }
  data[kind] = { file_id: fileId, date: new Date().toISOString() };
  const body = { message: `cookies ref (${kind}) update`, content: btoa(JSON.stringify(data, null, 1)), branch: "main" };
  if (sha) body.sha = sha;
  const r = await ghFetch(env, path, "PUT", body);
  return r.ok;
}

async function dispatchGH(env, workflowFile, inputs) {
  const res = await ghFetch(env, `/actions/workflows/${workflowFile}/dispatches`, "POST", { ref: "main", inputs });
  return res.ok;
}

async function cancelActiveRuns(env) {
  let count = 0;
  for (const st of ["in_progress", "queued"]) {
    const r = await ghFetch(env, `/actions/runs?status=${st}&per_page=10`);
    if (!r.ok) continue;
    const data = await r.json();
    for (const run of (data.workflow_runs || [])) {
      const cr = await ghFetch(env, `/actions/runs/${run.id}/cancel`, "POST");
      if (cr.ok || cr.status === 202) count++;
    }
  }
  return count;
}

async function getRunsSummary(env) {
  const r = await ghFetch(env, `/actions/runs?per_page=4`);
  if (!r.ok) return "❌ GitHub status nahi mil paya. GH_TOKEN check karo.";
  const data = await r.json();
  const runs = data.workflow_runs || [];
  if (!runs.length) return "ℹ️ Abhi tak koi cloud job nahi chali hai.";
  const lines = ["📊 Cloud Status & Live Logs:"];
  for (const run of runs) {
    const icon = run.status === "in_progress" ? "⏳" : run.status === "queued" ? "🕒" : (run.conclusion === "success" ? "✅" : run.conclusion === "cancelled" ? "🛑" : "❌");
    lines.push(`${icon} ${run.name} (${run.status}${run.conclusion ? "/" + run.conclusion : ""})\n🔗 ${run.html_url}`);
  }
  try {
    const mins = await monthMinutes(env);
    if (mins !== null) {
      const left = 2000 - mins;
      lines.push(`⏱ Is mahine GitHub ke ~${mins} minute lage (free: 2000) – bache ~${left > 0 ? left : 0} min` +
        (left < 300 ? "\n⚠️ Minute khatam hone wale hain!" : ""));
    }
  } catch (e) {}
  return lines.join("\n\n");
}

async function monthMinutes(env) {
  // v3.78: is mahine ke saare runs ka samay (har job minute me upar round – GitHub jaisa andaaza)
  const now = new Date();
  const start = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-01`;
  let total = 0, page = 1;
  while (page <= 5) {
    const r = await ghFetch(env, `/actions/runs?per_page=100&page=${page}&created=>=${start}`);
    if (!r.ok) return null;
    const d = await r.json();
    const runs = d.workflow_runs || [];
    for (const run of runs) {
      const a = Date.parse(run.run_started_at || run.created_at), b = Date.parse(run.updated_at);
      if (a && b && b > a) total += Math.ceil((b - a) / 60000);
    }
    if (runs.length < 100) break;
    page++;
  }
  return total;
}

async function tgReply(token, chatId, text, withKb = false) {
  const payload = { chat_id: chatId, text: String(text).slice(0, 4000) };
  if (withKb) payload.reply_markup = KEYBOARD;
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
