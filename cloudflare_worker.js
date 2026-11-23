// v3.83 Cloudflare Worker: FULL Telegram Control for Viral Gyaan Cloud VideoTool (24/7, $0/mo)
// Features:
//  - Persistent Menu Keyboard (Aaj shuru karo, Long Prompt, Status, /rok, /log, /purana, /guide)
//  - Instant 5-Shorts Micro-Beat Master Prompt & Long News+Fact Documentary Prompt
//  - REAL /rok -> cancels any active/queued GitHub Actions cloud render in 1 second!
//  - Live /status & /log -> shows live cloud job status & clickable GitHub log link!
//  - ZIP + caption "update" -> auto-updates your GitHub Cloud repo in 30s!
//  - /purana -> rolls back last cloud update!

const KEYBOARD = {
  keyboard: [
    [{ text: "🔥 /trends" }, { text: "▶️ Aaj shuru karo (5 Prompt)" }],
    [{ text: "🎬 Long Prompt" }, { text: "📊 /status" }, { text: "🛑 /rok" }],
    [{ text: "📜 /log" }, { text: "⏪ /purana" }, { text: "📖 /guide" }],
  ],
  resize_keyboard: true,
  is_persistent: true,
};

const SHORTS_PROMPT = `MERA TOPIC (1 se 5 topic likho, ya "AUTO" rehne do to 5 alag-alag viral trending topics khud chuno):
<<< AUTO >>>

You are India's #1 viral Hindi YouTube Shorts Director & Scriptwriter for "The Viral Gyaan" (science, army/defence, news, business, history, tech, crime/mystery, sports, influencers).
My automated VideoTool reads EVERY line, applies the EXACT category editing style you choose via MODE:, triggers real pro editing effects from your [tags], and picks visuals STRICTLY from your "||" hints (verified by AI Vision Judge + CLIP!).
Write 5 complete, high-retention Hindi Shorts scripts separated by a line with only ==== (each video MUST feel unique and matched to its category!).

1) CHOOSE CATEGORY EDITING MODE (line 1 of EACH script — controls colour grade, cut speed, film/particle layer, and SFX):
   MODE: science | army | news | business | history | mystery | sports | influencer | technology | general

2) STRICT MICRO-BEAT SCRIPT RULES (40-55 sec, 14-18 SHORT lines, 5-9 words per line — ONE single visual idea/emotion per line):
   - NEVER mix 2 contrasting ideas in 1 line! Split into 2 short lines so each emotion/subject gets its OWN exact visual.
   - HOOK (Line 1): Shocking/curious hook in first 2s. NEVER start with "दोस्तों" or "क्या आप जानते हैं".
   - Last line CTA (NO "||" on last line): ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।

3) PRO EDITING TAGS (put at END of Hindi line, right BEFORE "||" — use tastefully per category, max 4-5 tags per script):
   - [map: Place, Country] -> animated 3D satellite map zoom (great for army/news/history/geography)
   - [news: Short Headline | Source] -> yellow-highlighter newspaper/fact proof card (great for news/business/crime/history)
   - [label: 2024 / 828m / ₹500 Cr] -> crisp red typewriter date/number badge (great for science/business/sports)
   - [ink] -> dramatic red ink-splash transition on the biggest twist line!
   - SFX tags (max 2-3 per script — NEVER write [riser], opening riser is automatic!): [impact] on shock/army/reveal, [whoosh] on fast jump, [ding] on stat/fact, [typing] on tech/news.

4) VISUAL HINT RULES (MOST IMPORTANT — EVERY SINGLE LINE EXCEPT LAST CTA MUST HAVE "||"):
   - KEEP HINTS SHORT & SIMPLE (STRICTLY 3-4 lowercase English words describing what the camera sees — NEVER 6-8 word essays!):
     * Real people/events -> name + 2 words (e.g. "ISRO rocket launch", "Indian Army tank desert", "Ratan Tata Nano 2008"). NEVER use AI for real people/news!
     * Clean B-roll / nature / history -> 3-4 simple lowercase words (e.g. "desert sand dunes aerial", "hippopotamus swimming river", "ancient stone arrowheads", "cargo ship port aerial").
     * DO NOT capitalize non-person words (write "green grassland lake", NOT "Green Arabia Ancient Lake" — capitalized phrases trick person search!).
   - CUSTOM AI SCENE (ONLY 1-3 lines where real footage DOES NOT EXIST — e.g. inside black hole, prehistoric dinosaur, microscopic cell):
     * Format: || AI: <8-12 vivid realistic cinematic documentary words>
   - STRICTLY BANNED in "||" hints: "reconstruction", "reenactment", "examination", "prehistoric", "cinematic", "footage", "growth", "economy", "crisis", "secret", "interview", "podcast", "chart", "slide", "[YT]", "[X]", emojis, hashtags, bold (**), or numbering.

OUTPUT EXACTLY THIS (copy-paste ready for Telegram Bot):
MODE: <category>
TITLE: <2-4 crisp words> | <2-4 hook words>
<hook line> || <exact concrete visual hint>
<line 2> [map: Place, Country] || <exact concrete visual hint>
<line 3 with number> [label: 6400 KM] || <exact concrete visual hint>
<twist line> [ink] [impact] || <exact concrete visual hint>
...
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।
====
MODE: <different category for Script 2>
TITLE: <Script 2> | <hook>
...`;

const LONG_PROMPT = `MERA TOPIC (Long News + Fact Documentary Video):
<<< yahan apna topic ya breaking news + fact likho >>>

You are India's #1 Hindi Long-Form Documentary Director & Scriptwriter (Dhruv Rathee / Nitish Rajput / MagnatesMedia style) for "The Viral Gyaan".
My automated VideoTool renders 16:9 documentary videos with calm 5-second pacing, chapters, category-matched colour grading, animated maps, yellow-marker News cards, red spotlight callouts, and pinpoint visuals from your "||" hints.

STRUCTURE (3-6 min, 28-45 lines, 10-16 words per line, divided into 3-5 chapters using "## Chapter Name"):
- Line 1: LONG
- Line 2: MODE: news | army | science | business | history | mystery | sports | influencer | technology
- Line 3: TITLE: <documentary title> | <hook subtitle>
- Chapters: ## शुरुआत -> ## असली कहानी -> ## चौंकाने वाले आंकड़े -> ## बड़ा असर और निष्कर्ष

PRO EDITING TAGS (put at END of Hindi line, right BEFORE "||"):
- [map: City or Country] (1-2 geography lines)
- [news: Short Headline | Official Source] (2-3 proof/report/court/date lines -> yellow highlighter sweep!)
- [label: Year / Stat] (2-3 key timeline or number badges)
- [ink] or [impact] on major chapter reveals (NEVER write [riser], opening riser is automatic!).

VISUAL HINT RULES (EVERY LINE EXCEPT LAST CTA MUST HAVE "||"):
- KEEP HINTS SHORT (STRICTLY 3-4 simple lowercase English words — NO 'reconstruction', 'reenactment', 'examination', or unnecessary Capital letters):
  * Real events / news / defence / business / science -> add natural cues like "official footage", "launch", "press conference" (NEVER use AI for real people or real news!).
  * Historical / timeline lines -> add "archival photo" or "vintage photo".
  * Clean B-roll -> concrete physical scene + camera angle ("cargo ship port aerial view", "factory assembly line close up"), NEVER vague words ("economy", "growth", "crisis", "secret", "interview", "chart", "slide", or "[YT]"/"[X]" tags).
- IMPOSSIBLE / EXPLAINER RECONSTRUCTION (max 20% lines): || AI: <8-14 vivid realistic documentary words>.
- NO emojis, NO hashtags, NO bold (**), NO numbering, NO extra notes.

OUTPUT EXACTLY:
LONG
MODE: <category>
TITLE: <documentary title> | <hook subtitle>
## शुरुआत
<line 1> || <visual hint>
...
ऐसे ही गहरे रिसर्च वाले न्यूज़ और फैक्ट वीडियो के लिए चैनल को सब्सक्राइब ज़रूर करें।`;

const GUIDE_TEXT = `📖 VIRAL GYAAN CLOUD BOT (24×7)

• 🔥 /trends: Competitors ki top viral Shorts scan -> asli video dekh kar visual references + original script (approval ke baad video!).
• 👥 /competitors: Tracked competitor channels dekho/badlo (/competitors add @Handle ya del @Handle).
• ▶️ Aaj shuru karo (5 Prompt): ChatGPT/Gemini ke liye 5 Shorts ka micro-beat prompt milta hai.
• 🎬 Long Prompt: News + Fact documentary (16:9) ka prompt milta hai.
• Script bhejna: Seedha apni script paste karke bhejo (Long ke liye sabse upar LONG likho).
• 🛑 /rok: Cloud par chal rahi video ko turant rokta hai.
• 📊 /status aur 📜 /log: Live progress aur GitHub log link dikhata hai.
• 📦 Update: Koi bhi nayi .zip file caption "update" ke saath bhejo -> cloud 30 sec me update!
• ⏪ /purana: Pichhle version par wapas jaane ke liye.`;

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      return new Response("VideoTool Cloud Bridge v3.91 is LIVE!", { status: 200 });
    }
    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("ok", { status: 200 });
    }
    // v3.86 AUTO-QUEUE: cloud_run.py calls /queue-next when current video finishes
    if (update && update._vg_queue_next && env.TG_TOKEN && update.auth === env.TG_TOKEN.slice(0, 16)) {
      await popAndStartNext(env, update.chat_id || env.ALLOWED_CHAT_ID);
      return new Response("ok", { status: 200 });
    }
    // v3.83: buttons (Short / Long / meri awaaz) ka jawab
    if (update.callback_query) {
      const cdata = (update.callback_query.data || "");
      if (cdata.startsWith("tr:")) {
        const p = handleTrendCallback(env, update.callback_query);
        if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
      } else {
        await handleChoice(env, update.callback_query);
      }
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
      const kind = (both.includes("x.com") || both.includes("twitter") || /(^|[^a-z])x([^a-z]|$)/.test(both)) ? "x" : "youtube";
      const ok = await saveCookieRef(env, kind, doc.file_id);
      await tgReply(env.TG_TOKEN, chatId, ok
        ? `🍪 ${kind === "x" ? "X/Twitter" : "YouTube"} cookies mil gayi ✓ Agli video se apne aap lagengi.\n` +
          "Is message ko DELETE mat karna. Jaanch ke liye: SYSTEM JAANCH KARO"
        : "❌ Cookies save nahi hui – GH_TOKEN ko Contents: Read and write permission chahiye.", true);
      return new Response("ok", { status: 200 });
    }

    // v3.83: aapki awaaz (voice note / audio file) -> pehle chuni hui script ke saath video
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
        "☁️ VideoTool Cloud v3.91 LIVE hai!\nNeeche ke buttons use karo ya seedha script bhejo:", true);
      return new Response("ok", { status: 200 });
    }
    if (tl === "/guide" || text.includes("/guide")) {
      await tgReply(env.TG_TOKEN, chatId, GUIDE_TEXT, true);
      return new Response("ok", { status: 200 });
    }

    // 2b) v3.89: 🔥 /trends (Competitor Trend Radar + Real-Video Visual Reference + Approval Script)
    if (tl === "/trends" || tl === "/trend" || tl === "trends" || tl === "trend" || text.includes("/trends")) {
      const p = handleTrendsCommand(env, chatId);
      if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
      return new Response("ok", { status: 200 });
    }
    if (tl.startsWith("/competitors") || tl.startsWith("/comp")) {
      await handleCompetitorsCommand(env, chatId, text);
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

    // 4) REAL /rok -> Cancel running & queued GitHub Actions jobs + clear FIFO queue!
    if (tl === "/rok" || text.includes("/rok") || tl === "rok" || tl === "stop") {
      const canceled = await cancelActiveRuns(env);
      const qCleared = await clearQueue(env);
      await tgReply(env.TG_TOKEN, chatId, (canceled > 0 || qCleared > 0)
        ? `🛑 ${canceled} chal rahi video roki + ${qCleared} line (queue) me lagi scripts hata di gayi hain!`
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

    // 6b) v3.83: script aayi -> pehle poochho: Short / Long / meri awaaz (pehle seedha Short ban jaati thi)
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

// ---------------- v3.83: Short / Long / meri awaaz chunav ----------------
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
  const vmode = mode === "L" ? "LONG" : "SHORT";
  const items = splitScripts(orig).map(sc => ({ script: sc, mode: vmode, ts: Date.now() }));
  const res = await enqueueOrStart(env, items);
  if (res.started > 0 && res.queued > 0) {
    await edit(`🚀 1 ${vmode} video abhi shuru ho gayi + ${res.queued} videos line (queue) me lag gayi!\nEk ke baad ek apne aap banengi. /status se haal dekho, /rok se sab roko.`);
  } else if (res.started > 0) {
    await edit(`🚀 ${vmode} video cloud par shuru!\nBante hi haatho-haath video + download link yahin aayegi. /status se haal dekho, /rok se roko.`);
  } else if (res.queued > 0) {
    await edit(`📋 Line (Queue) me lag gayi! (Abhi queue me ${res.queueLen} script)\nPehli video complete hote hi apne aap shuru hogi. /rok se sab cancel kar sakte ho.`);
  } else {
    await edit("❌ GitHub render trigger fail ho gaya. GH_TOKEN aur GH_REPO check karo.");
  }
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

// ---------------- v3.86: 1-by-1 Automatic Multi-Script FIFO Queue ----------------
const QUEUE_PATH = "/contents/seekha/video_queue.json";
async function readQueue(env) {
  try {
    const g = await ghFetch(env, QUEUE_PATH);
    if (!g.ok) return { items: [], sha: undefined };
    const j = await g.json();
    const arr = JSON.parse(b64d(j.content) || "[]");
    return { items: Array.isArray(arr) ? arr : [], sha: j.sha };
  } catch (e) { return { items: [], sha: undefined }; }
}
async function saveQueue(env, items, sha) {
  const body = { message: `queue update (${items.length})`, content: b64e(JSON.stringify(items)), branch: "main" };
  if (sha) body.sha = sha;
  const r = await ghFetch(env, QUEUE_PATH, "PUT", body);
  return r.ok;
}
async function clearQueue(env) {
  const q = await readQueue(env);
  if (!q.items.length) return 0;
  await saveQueue(env, [], q.sha);
  return q.items.length;
}
async function hasActiveVideoRun(env) {
  for (const st of ["in_progress", "queued"]) {
    const r = await ghFetch(env, `/actions/workflows/make_video.yml/runs?status=${st}&per_page=3`);
    if (r.ok) {
      const j = await r.json();
      if ((j.workflow_runs || []).length > 0) return true;
    }
  }
  return false;
}
async function enqueueOrStart(env, newItems) {
  const busy = await hasActiveVideoRun(env);
  let started = 0, toQueue = [];
  if (!busy && newItems.length > 0) {
    const ok = await dispatchGH(env, "make_video.yml", { script: newItems[0].script, mode: newItems[0].mode });
    if (ok) { started = 1; toQueue = newItems.slice(1); }
    else { return { started: 0, queued: 0, queueLen: 0 }; }
  } else {
    toQueue = newItems;
  }
  let qLen = 0;
  if (toQueue.length > 0) {
    const q = await readQueue(env);
    const merged = q.items.concat(toQueue).slice(0, 15);
    const saved = await saveQueue(env, merged, q.sha);
    qLen = saved ? merged.length : q.items.length;
    if (!saved && started === 0) return { started: 0, queued: 0, queueLen: q.items.length };
  }
  return { started, queued: toQueue.length, queueLen: qLen };
}
async function popAndStartNext(env, chatId) {
  const q = await readQueue(env);
  if (!q.items.length) return;
  const next = q.items[0];
  const rest = q.items.slice(1);
  await saveQueue(env, rest, q.sha);
  const ok = await dispatchGH(env, "make_video.yml", { script: next.script, mode: next.mode || "SHORT" });
  if (chatId) {
    const firstLn = (next.script || "").split("\n").find(l => l.trim() && !/^(MODE|TITLE|LONG)/i.test(l.trim())) || "Agli video";
    await tgReply(env.TG_TOKEN, chatId, ok
      ? `▶️ Queue se agli ${next.mode || "SHORT"} video shuru ho gayi! (Baaki ${rest.length} line me)\n${firstLn.slice(0, 60)}`
      : "⚠️ Queue se agli video start nahi ho paayi.", true);
  }
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


// ---------------- v3.89: Competitor Trend Radar + Real-Video Visual Reference + Approval Script ----------------
const DEFAULT_COMPETITORS = [
  "@FactsMine",
  "@FactTechz",
  "@dhruvrathee",
  "@NitishRajput",
  "@GetsetflyFACT",
  "@AbhiandNiyu",
];
const COMP_PATH = "/contents/seekha/competitors.json";
const TRENDS_CACHE_PATH = "/contents/seekha/trends_cache.json";
const TREND_DRAFT_PATH = "/contents/seekha/trend_draft.json";

async function readGhJson(env, path, fallback) {
  try {
    const g = await ghFetch(env, path);
    if (!g.ok) return { data: fallback, sha: undefined };
    const j = await g.json();
    const d = JSON.parse(b64d(j.content) || "null");
    return { data: d ?? fallback, sha: j.sha };
  } catch (e) {
    return { data: fallback, sha: undefined };
  }
}

async function writeGhJson(env, path, data, sha, message = "bot state update") {
  const body = { message, content: b64e(JSON.stringify(data, null, 1)), branch: "main" };
  if (sha) body.sha = sha;
  const r = await ghFetch(env, path, "PUT", body);
  return r.ok;
}

function parseIsoDurationSec(iso) {
  const m = String(iso || "").match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!m) return 0;
  return (parseInt(m[1] || "0", 10) * 3600) + (parseInt(m[2] || "0", 10) * 60) + parseInt(m[3] || "0", 10);
}

function fmtViews(v) {
  const n = Number(v || 0);
  if (n >= 1e7) return `${(n / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `${(n / 1e5).toFixed(1)}L`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

async function handleCompetitorsCommand(env, chatId, text) {
  const parts = text.trim().split(/\s+/);
  const sub = (parts[1] || "").toLowerCase();
  const rawH = (parts[2] || "").trim();
  const cur = await readGhJson(env, COMP_PATH, DEFAULT_COMPETITORS);
  let list = Array.isArray(cur.data) && cur.data.length ? cur.data.slice() : DEFAULT_COMPETITORS.slice();

  if (sub === "add" && rawH) {
    const h = rawH.startsWith("@") ? rawH : "@" + rawH.replace(/^.*youtube\.com\/@?/i, "").replace(/\/.*$/, "");
    if (!list.some(x => x.toLowerCase() === h.toLowerCase())) {
      list.push(h);
      list = list.slice(0, 12);
      await writeGhJson(env, COMP_PATH, list, cur.sha, `competitors add ${h}`);
    }
    await tgReply(env.TG_TOKEN, chatId, `✅ ${h} list me jud gaya!\n\nAbhi tracked channels (${list.length}):\n` + list.join("\n"), true);
    return;
  }
  if ((sub === "del" || sub === "remove") && rawH) {
    const h = (rawH.startsWith("@") ? rawH : "@" + rawH).toLowerCase();
    const next = list.filter(x => x.toLowerCase() !== h);
    await writeGhJson(env, COMP_PATH, next.length ? next : DEFAULT_COMPETITORS, cur.sha, `competitors del ${rawH}`);
    await tgReply(env.TG_TOKEN, chatId, `🗑 ${rawH} hata diya.\n\nAbhi tracked channels:\n` + (next.length ? next : DEFAULT_COMPETITORS).join("\n"), true);
    return;
  }
  if (sub === "reset") {
    await writeGhJson(env, COMP_PATH, DEFAULT_COMPETITORS, cur.sha, "competitors reset");
    await tgReply(env.TG_TOKEN, chatId, "🔄 Default 6 competitor channels restore ho gaye:\n" + DEFAULT_COMPETITORS.join("\n"), true);
    return;
  }
  await tgReply(env.TG_TOKEN, chatId,
    `👥 Tracked Competitor Channels (${list.length}):\n` + list.join("\n") +
    `\n\nBadalne ke liye:\n• /competitors add @ChannelName\n• /competitors del @ChannelName\n• /competitors reset`, true);
}

async function scanCompetitorTrends(env) {
  const ytKey = (env.YOUTUBE_KEY || "").trim();
  const cur = await readGhJson(env, COMP_PATH, DEFAULT_COMPETITORS);
  const handles = (Array.isArray(cur.data) && cur.data.length ? cur.data : DEFAULT_COMPETITORS).slice(0, 10);

  // 1) Resolve uploads playlist for each handle (~1 quota unit each)
  const chanTasks = handles.map(async (h) => {
    try {
      const clean = h.replace(/^@/, "");
      const r = await fetch(`https://www.googleapis.com/youtube/v3/channels?part=contentDetails,snippet&forHandle=${encodeURIComponent(clean)}&key=${encodeURIComponent(ytKey)}`);
      if (!r.ok) return null;
      const j = await r.json();
      const it = (j.items || [])[0];
      const up = it && it.contentDetails && it.contentDetails.relatedPlaylists && it.contentDetails.relatedPlaylists.uploads;
      if (!up) return null;
      return { handle: h, name: (it.snippet && it.snippet.title) || h, uploads: up };
    } catch (e) { return null; }
  });
  const chans = (await Promise.all(chanTasks)).filter(Boolean);
  if (!chans.length) return [];

  // 2) Fetch last 6 uploads per channel (~1 quota unit each)
  const vidTasks = chans.map(async (c) => {
    try {
      const r = await fetch(`https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId=${encodeURIComponent(c.uploads)}&maxResults=6&key=${encodeURIComponent(ytKey)}`);
      if (!r.ok) return [];
      const j = await r.json();
      return (j.items || []).map(x => ({ id: x.contentDetails && x.contentDetails.videoId, channel: c.name, handle: c.handle })).filter(x => x.id);
    } catch (e) { return []; }
  });
  const rawList = (await Promise.all(vidTasks)).flat();
  const idMap = new Map();
  for (const x of rawList) if (!idMap.has(x.id)) idMap.set(x.id, x);
  const ids = Array.from(idMap.keys()).slice(0, 48);
  if (!ids.length) return [];

  // 3) Batch video stats + duration (1 quota unit total!)
  const vr = await fetch(`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${ids.join(",")}&key=${encodeURIComponent(ytKey)}`);
  if (!vr.ok) return [];
  const vj = await vr.json();
  const now = Date.now();
  const all = [];
  for (const v of (vj.items || [])) {
    const dur = parseIsoDurationSec(v.contentDetails && v.contentDetails.duration);
    if (dur < 12 || dur > 210) continue; // Focus on Shorts / short-form (<= 3.5 min)
    const pubMs = Date.parse((v.snippet && v.snippet.publishedAt) || "");
    const ageH = Math.max(6, (now - (pubMs || now)) / 3600000);
    const views = Number((v.statistics && v.statistics.viewCount) || 0);
    if (views < 1000) continue;
    const meta = idMap.get(v.id) || {};
    all.push({
      id: v.id,
      title: (v.snippet && v.snippet.title) || "Untitled",
      channel: meta.channel || (v.snippet && v.snippet.channelTitle) || "",
      handle: meta.handle || "",
      views,
      dur,
      ageDays: Math.round(ageH / 24),
      score: views / Math.pow(ageH, 0.85),
      url: `https://www.youtube.com/watch?v=${v.id}`,
    });
  }
  // Prefer videos from last 35 days; fallback to all if < 5
  const recent = all.filter(x => x.ageDays <= 35);
  const pool = recent.length >= 5 ? recent : all;
  pool.sort((a, b) => b.score - a.score);

  // Pick Top 5 diverse (max 1 per channel first, then fill)
  const picked = [];
  const usedCh = new Set();
  for (const v of pool) {
    if (picked.length >= 5) break;
    if (!usedCh.has(v.handle)) { picked.push(v); usedCh.add(v.handle); }
  }
  for (const v of pool) {
    if (picked.length >= 5) break;
    if (!picked.some(p => p.id === v.id)) picked.push(v);
  }
  return picked;
}

async function handleTrendsCommand(env, chatId) {
  if (!env.YOUTUBE_KEY || !env.GEMINI_KEY) {
    await tgReply(env.TG_TOKEN, chatId,
      "🔑 /trends chalane ke liye bas 1 baar Cloudflare Worker (vg-bots) me 2 secrets add karne hain (0 GitHub minutes lagte hain!):\n\n" +
      "1️⃣ dash.cloudflare.com -> Workers & Pages -> vg-bots -> Settings -> Variables and Secrets\n" +
      "2️⃣ Add: YOUTUBE_KEY (aapki YouTube API key)\n" +
      "3️⃣ Add: GEMINI_KEY (aapki Gemini API key)\n\nAdd karte hi 🔥 /trends turant kaam karega!", true);
    return;
  }
  const waitRes = await tgApi(env, "sendMessage", { chat_id: chatId, text: "🔥 Competitor channels ki viral Shorts scan kar raha hoon (~5 sec)..." });
  const waitMsg = waitRes.ok ? (await waitRes.json()).result : null;
  const trends = await scanCompetitorTrends(env);
  if (!trends.length) {
    const errTxt = "❌ Abhi koi trending Short nahi mili (YOUTUBE_KEY quota ya handles check karein).";
    if (waitMsg) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsg.message_id, text: errTxt });
    else await tgReply(env.TG_TOKEN, chatId, errTxt, true);
    return;
  }
  const prev = await readGhJson(env, TRENDS_CACHE_PATH, {});
  await writeGhJson(env, TRENDS_CACHE_PATH, { items: trends, ts: Date.now() }, prev.sha, "trends cache update");

  const lines = ["🔥 Top 5 Viral Competitor Shorts (Real Video Visual Reference ke liye number tap karo):\n"];
  trends.forEach((v, i) => {
    lines.push(`${i + 1}️⃣ ${v.title.slice(0, 72)}\n   📺 ${v.channel} • 👁 ${fmtViews(v.views)} (${v.ageDays}d) • 🔗 ${v.url}`);
  });
  lines.push("\n👇 Jis topic par tap karoge, Gemini uska asli video dekh kar visual references + 100% original Hindi script dega (aapke approval ke baad hi video banegi):");

  const kb = {
    inline_keyboard: [
      trends.slice(0, 3).map((_, i) => ({ text: `${i + 1}️⃣ Script Banao`, callback_data: `tr:pick:${i}` })),
      trends.slice(3, 5).map((_, i) => ({ text: `${i + 4}️⃣ Script Banao`, callback_data: `tr:pick:${i + 3}` })).concat([{ text: "🔄 Refresh", callback_data: "tr:ref" }]),
    ],
  };
  if (waitMsg) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsg.message_id, text: lines.join("\n"), disable_web_page_preview: true, reply_markup: kb });
  } else {
    await tgApi(env, "sendMessage", { chat_id: chatId, text: lines.join("\n"), disable_web_page_preview: true, reply_markup: kb });
  }
}

async function discoverGeminiModels(gKey) {
  // v3.91: Dynamically fetch active Flash models from /v1beta/models so 404 model retirements NEVER break /trends!
  const defaults = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"];
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(gKey)}`);
    if (!r.ok) return defaults;
    const j = await r.json();
    const avail = (j.models || [])
      .filter(m => Array.isArray(m.supportedGenerationMethods) && m.supportedGenerationMethods.includes("generateContent"))
      .map(m => String(m.name || "").replace(/^models\//, ""))
      .filter(n => /gemini/i.test(n) && /flash/i.test(n) && !/(tts|audio|image|embedding|live|robotics|computer|customtools)/i.test(n));
    // Sort newest version first (prefer non-lite Flash first, then Flash-Lite)
    avail.sort((a, b) => {
      const va = parseFloat((a.match(/gemini-(\d+(?:\.\d+)?)/i) || [0, "0"])[1]);
      const vb = parseFloat((b.match(/gemini-(\d+(?:\.\d+)?)/i) || [0, "0"])[1]);
      if (vb !== va) return vb - va;
      const la = /lite/i.test(a) ? 1 : 0;
      const lb = /lite/i.test(b) ? 1 : 0;
      return la - lb;
    });
    const out = [];
    for (const m of avail.concat(defaults)) {
      if (m && !out.includes(m)) out.push(m);
    }
    return out.slice(0, 5);
  } catch (e) {
    return defaults;
  }
}

async function fetchYouTubeTranscriptText(videoId) {
  // v3.91: Lightweight public YouTube captions/transcript fetcher (0 GitHub minutes, 0 yt-dlp)
  try {
    const page = await fetch(`https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`, {
      headers: { "Accept-Language": "hi-IN,hi;q=0.9,en;q=0.8", "User-Agent": "Mozilla/5.0" },
    });
    if (!page.ok) return "";
    const html = await page.text();
    const m = html.match(/"captionTracks":(\[[\s\S]*?\])/);
    if (!m) return "";
    const tracks = JSON.parse(m[1]);
    if (!Array.isArray(tracks) || !tracks.length) return "";
    const pick = tracks.find(t => /^hi/i.test(t.languageCode || "")) || tracks.find(t => /^en/i.test(t.languageCode || "")) || tracks[0];
    if (!pick || !pick.baseUrl) return "";
    const tr = await fetch(pick.baseUrl);
    if (!tr.ok) return "";
    const xml = await tr.text();
    const text = xml
      .replace(/<[^>]+>/g, " ")
      .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#39;/g, "'").replace(/&quot;/g, '"')
      .replace(/\s+/g, " ").trim();
    return text.slice(0, 2200);
  } catch (e) {
    return "";
  }
}

async function callGeminiTrendScript(env, video, rewrite = false) {
  const gKey = (env.GEMINI_KEY || "").trim();
  const basePrompt = `You are India's #1 viral Hindi YouTube Shorts Director for "The Viral Gyaan".
TASK:
1) Study this reference viral YouTube Short. Ignore the competitor's editing/transitions — focus ONLY on the factual topic and WHAT REAL FOOTAGES, IMAGES, OBJECTS, PEOPLE, AND SCENES best explain it.
2) Write a 100% ORIGINAL Hindi YouTube Short script on this same viral topic (NEVER copy/translate the competitor's wording — use a fresh, gripping hook and your own structure${rewrite ? " with a COMPLETELY DIFFERENT opening hook and angle than before" : ""}).
3) For every script line, put camera-exact English visual references after "||" (3-4 simple lowercase English words — NO "reconstruction", "reenactment", "examination", "interview", "chart", or capitalized non-person phrases; NO "[YT]"/"[X]" tags).

OUTPUT FORMAT (strictly follow these two sections):
VISUAL_REFS:
- <visual reference 1>
- <visual reference 2>
- <visual reference 3>

SCRIPT:
MODE: <science | army | news | business | history | mystery | sports | influencer | technology | general>
TITLE: <2-4 crisp words> | <2-4 hook words>
<14-17 short punchy Hindi lines, 5-9 words each, tasteful [map:]/[news:]/[impact] tags max 3 total (NEVER write [riser] or [gola:] or [label:]), EVERY line except last CTA ends with "|| <3-4 simple lowercase English visual words>">
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।`;

  const models = await discoverGeminiModels(gKey);
  const errs = [];

  // Step 1: Try native YouTube URL video watch on discovered active Flash models (0 download, 0 GitHub minutes)
  for (const model of models.slice(0, 2)) {
    try {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(gKey)}`;
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{
            role: "user",
            parts: [
              { fileData: { fileUri: video.url, mimeType: "video/*" } },
              { text: basePrompt },
            ],
          }],
        }),
      });
      if (r.ok) {
        const j = await r.json();
        const out = j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts
          ? j.candidates[0].content.parts.map(p => p.text || "").join("\n").trim() : "";
        if (out && out.includes("MODE:")) return { text: out, mode: "video", model };
      } else {
        const eb = await r.text();
        errs.push(`${model}(vid): ${r.status} ${eb.slice(0, 80)}`);
      }
    } catch (e) {
      errs.push(`${model}(vid): ${String(e).slice(0, 60)}`);
    }
  }

  // Step 2: Automatic Transcript/Captions + Topic fallback across all active Flash models (never fails on 404!)
  const transcript = await fetchYouTubeTranscriptText(video.id);
  const ctxBlock = transcript
    ? `Reference viral Short title: "${video.title}" (Channel: ${video.channel}).\nSpoken transcript of reference video (DO NOT copy wording — extract only core facts & visual scenes):\n${transcript}`
    : `Reference viral Short title: "${video.title}" (Channel: ${video.channel}).`;
  const fbPrompt = basePrompt + "\n\nREFERENCE INFO:\n" + ctxBlock;

  for (const model of models) {
    try {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(gKey)}`;
      const r2 = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: fbPrompt }] }] }),
      });
      if (r2.ok) {
        const j2 = await r2.json();
        const out2 = j2.candidates && j2.candidates[0] && j2.candidates[0].content && j2.candidates[0].content.parts
          ? j2.candidates[0].content.parts.map(p => p.text || "").join("\n").trim() : "";
        if (out2) return { text: out2, mode: transcript ? "transcript" : "topic", model };
      } else {
        const eb = await r2.text();
        errs.push(`${model}: ${r2.status} ${eb.slice(0, 80)}`);
      }
    } catch (e) {
      errs.push(`${model}: ${String(e).slice(0, 60)}`);
    }
  }
  return { text: "", error: errs.slice(0, 3).join(" | ") };
}

function parseTrendGeminiOutput(raw) {
  const clean = String(raw || "").replace(/```[a-z]*\n?/gi, "").replace(/```/g, "").trim();
  const idx = clean.indexOf("SCRIPT:");
  if (idx === -1) return { refs: "", script: clean };
  const refs = clean.slice(0, idx).replace(/VISUAL_REFS:/i, "").trim();
  const script = clean.slice(idx + 7).trim();
  return { refs, script };
}

async function handleTrendCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  const msgId = cq.message ? cq.message.message_id : null;
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const data = cq.data || "";

  if (data === "tr:ref") {
    await handleTrendsCommand(env, chatId);
    return;
  }
  if (data === "tr:no") {
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "❌ Cancel — script discard kar di gayi." });
    return;
  }
  if (data === "tr:go") {
    const dr = await readGhJson(env, TREND_DRAFT_PATH, null);
    if (!dr.data || !dr.data.script) {
      if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "⚠️ Draft script nahi mili. Dobara 🔥 /trends chalao." });
      return;
    }
    const res = await enqueueOrStart(env, [{ script: dr.data.script, mode: "SHORT", ts: Date.now() }]);
    const reply = res.started > 0
      ? "🚀 Approved! SHORT video cloud par shuru ho gayi hai!\nBante hi haatho-haath video + download link yahin aayegi."
      : (res.queued > 0
        ? `📋 Approved! Queue me lag gayi (queue: ${res.queueLen}). Pehli video khatam hote hi apne aap chalegi.`
        : "❌ GitHub render trigger fail ho gaya.");
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: reply });
    return;
  }

  let video = null;
  const rewrite = data === "tr:rw";
  if (rewrite) {
    const dr = await readGhJson(env, TREND_DRAFT_PATH, null);
    video = dr.data && dr.data.video;
  } else if (data.startsWith("tr:pick:")) {
    const idx = parseInt(data.split(":")[2] || "0", 10);
    const cache = await readGhJson(env, TRENDS_CACHE_PATH, { items: [] });
    video = (cache.data && cache.data.items || [])[idx];
  }
  if (!video) {
    await tgReply(env.TG_TOKEN, chatId, "⚠️ Purana list expire ho gaya — dobara 🔥 /trends dabao.", true);
    return;
  }

  const statusRes = await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: `👀 Gemini asli YouTube video dekh kar visual references aur ${rewrite ? "naya angle" : "original"} Hindi script likh raha hoon (~15 sec)...\n🔗 ${video.url}`,
    disable_web_page_preview: true,
  });
  const statusMsg = statusRes.ok ? (await statusRes.json()).result : null;

  const gen = await callGeminiTrendScript(env, video, rewrite);
  if (!gen || !gen.text) {
    const failTxt = `❌ Script nahi ban payi.\n🔍 Wajah: ${(gen && gen.error) || "GEMINI_KEY ya quota check karo"}`;
    if (statusMsg) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: statusMsg.message_id, text: failTxt });
    else await tgReply(env.TG_TOKEN, chatId, failTxt, true);
    return;
  }

  const parsed = parseTrendGeminiOutput(gen.text);
  const oldDr = await readGhJson(env, TREND_DRAFT_PATH, null);
  await writeGhJson(env, TREND_DRAFT_PATH, { video, script: parsed.script, refs: parsed.refs, ts: Date.now() }, oldDr.sha, "trend draft script");

  const badge = gen.mode === "video"
    ? `👀 Asli YouTube video dekh kar visual references nikaale ✓ (${gen.model})`
    : (gen.mode === "transcript"
      ? `📝 YouTube transcript se 100% original script + visual hints banaye ✓ (${gen.model})`
      : `⚡ Viral topic se 100% original script + visual hints banaye ✓ (${gen.model})`);
  const preview = `${badge}\n\n${parsed.refs ? "🎬 Visual References:\n" + parsed.refs + "\n\n" : ""}📝 ORIGINAL SCRIPT (Padh kar approve karo):\n\n${parsed.script}`.slice(0, 3950);
  const approveKb = {
    inline_keyboard: [
      [{ text: "✅ Haan, Video Banao", callback_data: "tr:go" }],
      [{ text: "✏️ Dobara Likho", callback_data: "tr:rw" }, { text: "❌ Cancel", callback_data: "tr:no" }],
    ],
  };
  if (statusMsg) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: statusMsg.message_id, text: preview, reply_markup: approveKb });
  } else {
    await tgApi(env, "sendMessage", { chat_id: chatId, text: preview, reply_markup: approveKb });
  }
}
