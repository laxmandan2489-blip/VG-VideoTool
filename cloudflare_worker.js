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
• 📊 /status: Live progress | 📜 /log: Seedha downloadable log + Visual Report files.
• 📂 /republish: Aakhri 10 videos (Cover+Story sahit) 1-tap dobara upload.
• 📤 Video bhejo (<20MB) ya /publish <catbox_link> | <Title> (20-200MB).
• 🎨 /vfilter: Visual Quality Filter ON/OFF.
• 📦 Update: Koi bhi nayi .zip file caption "update" ke saath bhejo -> cloud 30 sec me update!
• ⏪ /purana: Pichhle version par wapas jaane ke liye.`;

export default {
  async fetch(request, env, ctx) {
    if (request.method === "GET" || request.method === "HEAD") {
      const u = new URL(request.url);
      if (u.pathname.startsWith("/media/tg/")) {
        return handleTgMediaBridge(env, u.pathname, u.searchParams.get("fb") || "", request.method === "HEAD");
      }
      if (u.pathname === "/media/proxy") {
        return handleProxyMediaBridge(u.searchParams.get("u") || "", u.searchParams.get("t") || "mp4", request.method === "HEAD");
      }
      return new Response("VideoTool Cloud Bridge v4.06 is LIVE!", { status: 200 });
    }
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
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
    // v3.93 AUTO-PUBLISH: cloud_run.py registers finished video metadata & sends 1-tap Publish Approval Card
    if (update && update._vg_register_publish && env.TG_TOKEN && update.auth === env.TG_TOKEN.slice(0, 16)) {
      await registerPublishCard(env, update);
      return new Response("ok", { status: 200 });
    }
    // v4.02 LAST-RUN LOG: cloud_run.py saves downloadable log_url & vrep_file_id for instant /log command
    if (update && update._vg_register_log && env.TG_TOKEN && update.auth === env.TG_TOKEN.slice(0, 16)) {
      await registerRunLog(env, update);
      return new Response("ok", { status: 200 });
    }
    // v3.83: buttons (Short / Long / meri awaaz) ka jawab
    if (update.callback_query) {
      const cdata = (update.callback_query.data || "");
      if (cdata.startsWith("tr:")) {
        const p = handleTrendCallback(env, update.callback_query);
        if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
      } else if (cdata.startsWith("pub:")) {
        const p = handlePublishCallback(env, update.callback_query);
        if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
      } else if (cdata.startsWith("vf:")) {
        await handleVfilterCallback(env, update.callback_query);
      } else if (cdata.startsWith("rb:")) {
        await handleRollbackConfirm(env, update.callback_query);
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

    // v4.06: Gallery / Forwarded Video (ya video/mp4 File) -> turant 1-Tap Auto-Publish Card (BEFORE `if (!text) return`!)
    const vidObj = msg.video || (doc && /^video\//.test(doc.mime_type || "") ? doc : null);
    if (vidObj && vidObj.file_id && update.message) {
      await handleForwardedVideoPublish(env, chatId, vidObj, msg.caption || "");
      return new Response("ok", { status: 200 });
    }

    // v3.83: aapki awaaz (voice note / audio file) -> pehle chuni hui script ke saath video
    const aud = msg.voice || msg.audio || (doc && /^audio\//.test(doc.mime_type || "") ? doc : null);
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
        "☁️ VideoTool Cloud v4.06 LIVE hai!\nNeeche ke buttons use karo, script bhejo, ya purani video (<20MB) forward karo:", true);
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

    // 5a) Live /status from GitHub Actions API
    if (tl === "/status" || text.includes("/status")) {
      const summary = await getRunsSummary(env);
      await tgReply(env.TG_TOKEN, chatId, summary, true);
      return new Response("ok", { status: 200 });
    }

    // 5b) v4.02 Instant /log -> sends actual downloadable last_video_log.txt + VISUAL_REPORT.md in Telegram!
    if (tl === "/log" || text.includes("/log") || tl === "log") {
      await sendLatestLogFiles(env, chatId);
      return new Response("ok", { status: 200 });
    }

    // 5c) v4.02 Reversible Visual Quality Filter Toggle (/vfilter on | /vfilter off | /vfilter)
    if (tl === "/vfilter" || tl.startsWith("/vfilter ")) {
      const arg = tl.replace("/vfilter", "").trim();
      if (arg === "off" || arg === "band" || arg === "0") {
        await setVfilterState(env, chatId, false);
      } else if (arg === "on" || arg === "chalu" || arg === "1") {
        await setVfilterState(env, chatId, true);
      } else {
        await showVfilterMenu(env, chatId);
      }
      return new Response("ok", { status: 200 });
    }

    // 5d) v4.05 /republish -> Show last 10 rendered videos (with saved Cover + Story + Caption) for 1-tap Re-Upload!
    if (tl === "/republish" || tl === "/reupload" || tl.startsWith("/republish ")) {
      await showRepublishVault(env, chatId);
      return new Response("ok", { status: 200 });
    }

    // 5e) v4.05 /publish <direct_mp4_url> | <Title> -> Publish any 20MB-200MB old video via link!
    if (tl.startsWith("/publish ")) {
      await handleManualPublishUrl(env, chatId, text.slice(9).trim());
      return new Response("ok", { status: 200 });
    }

    // 6) v3.93 Rollback /purana with 1-tap safety confirmation (stops accidental pocket-taps!)
    if (tl === "/purana" || text.includes("/purana")) {
      await tgApi(env, "sendMessage", {
        chat_id: chatId,
        text: "⚠️ Kya sach me pichhle version par rollback (/purana) karna hai?",
        reply_markup: {
          inline_keyboard: [
            [{ text: "✅ Haan, Rollback Karo", callback_data: "rb:go" }, { text: "❌ Cancel", callback_data: "rb:no" }],
          ],
        },
      });
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

const TREND_CATEGORIES = {
  facts: {
    label: "🧠 Facts & Science",
    modeHint: "science | history | mystery | general",
    visualRule: "Use exact real-world objects, places, historical photos, or science scenes.",
    handles: null, // uses saved /competitors list (DEFAULT_COMPETITORS)
  },
  tech: {
    label: "📱 Tech & Gadgets",
    modeHint: "technology",
    visualRule: "CRITICAL FOR TECH: Every '||' visual hint MUST include the EXACT smartphone/gadget/software model name (e.g., 'iphone 17 pro camera closeup', 'samsung s26 ultra screen', 'android 16 feature demo') so exact product visuals load — NEVER generic words like 'smartphone' or 'technology'.",
    handles: ["@TechBurner", "@TechnicalGuruji", "@TrakinTech", "@TechBar", "@GyanTherapy", "@Beebom"],
  },
  movies: {
    label: "🎬 Movies & Reviews",
    modeHint: "influencer",
    visualRule: "CRITICAL FOR MOVIES: Every '||' visual hint MUST include the EXACT movie/web-series title or lead actor/scene name (e.g., 'pushpa 2 trailer action', 'kalki movie scene closeup') and keep narration 100% original review/breakdown style (copyright-safe).",
    handles: ["@PJExplained", "@FilmiIndian", "@YogiBoltaHai", "@ComicVerse", "@BnfTV", "@MenOfCulture"],
  },
  updates: {
    label: "🚀 YT / IG / AI Updates",
    modeHint: "technology | news",
    visualRule: "CRITICAL FOR APP/PLATFORM UPDATES: Every '||' visual hint MUST name the EXACT platform/app screen or AI tool (e.g., 'instagram reels interface screen', 'youtube studio analytics mobile', 'whatsapp new update feature', 'chatgpt app screen').",
    handles: ["@ManojDey", "@CreatorSearch2", "@TechnicalYogi", "@DecodingYT", "@TechBurnerShorts", "@aiuncovered"],
  },
  mix: {
    label: "🌍 Mix All (Top Viral)",
    modeHint: "technology | science | news | influencer | history | mystery",
    visualRule: "Include the exact product/movie/app/person/place name in every '||' visual hint so exact visuals load.",
    handles: ["@FactsMine", "@FactTechz", "@TechBurner", "@TrakinTech", "@PJExplained", "@FilmiIndian", "@ManojDey", "@NitishRajput"],
  },
};

async function scanCompetitorTrends(env, catKey = "facts", excludeIds = []) {
  const ytKey = (env.YOUTUBE_KEY || "").trim();
  const cat = TREND_CATEGORIES[catKey] || TREND_CATEGORIES.facts;
  let handles = cat.handles;
  if (!handles) {
    const cur = await readGhJson(env, COMP_PATH, DEFAULT_COMPETITORS);
    handles = (Array.isArray(cur.data) && cur.data.length ? cur.data : DEFAULT_COMPETITORS).slice(0, 10);
  }
  const seenSet = new Set((excludeIds || []).map(String));

  // 1) Resolve uploads playlist for each handle (~1 quota unit each)
  const chanTasks = handles.map(async (h) => {
    try {
      const clean = h.replace(/^@/, "");
      const r = await fetchWithTimeout(`https://www.googleapis.com/youtube/v3/channels?part=contentDetails,snippet&forHandle=${encodeURIComponent(clean)}&key=${encodeURIComponent(ytKey)}`, {}, 6000);
      if (!r.ok) return null;
      const j = await r.json();
      const it = (j.items || [])[0];
      const up = it && it.contentDetails && it.contentDetails.relatedPlaylists && it.contentDetails.relatedPlaylists.uploads;
      if (!up) return null;
      return { handle: h, name: (it.snippet && it.snippet.title) || h, uploads: up };
    } catch (e) { return null; }
  });
  const chans = (await Promise.all(chanTasks)).filter(Boolean);
  if (!chans.length) return { items: [], recycled: false };

  // 2) Fetch last 12 uploads per channel (same 1 quota unit -> deep fresh pool for Refresh!)
  const vidTasks = chans.map(async (c) => {
    try {
      const r = await fetchWithTimeout(`https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId=${encodeURIComponent(c.uploads)}&maxResults=12&key=${encodeURIComponent(ytKey)}`, {}, 6000);
      if (!r.ok) return [];
      const j = await r.json();
      return (j.items || []).map(x => ({ id: x.contentDetails && x.contentDetails.videoId, channel: c.name, handle: c.handle })).filter(x => x.id);
    } catch (e) { return []; }
  });
  const rawList = (await Promise.all(vidTasks)).flat();
  const idMap = new Map();
  for (const x of rawList) if (!idMap.has(x.id)) idMap.set(x.id, x);
  const allIds = Array.from(idMap.keys());
  if (!allIds.length) return { items: [], recycled: false };

  // 3) Batch video stats + duration (up to 2 batches of 50 = 2 quota units max!)
  const vItems = [];
  for (let off = 0; off < Math.min(allIds.length, 100); off += 50) {
    const chunk = allIds.slice(off, off + 50);
    try {
      const vr = await fetchWithTimeout(`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${chunk.join(",")}&key=${encodeURIComponent(ytKey)}`, {}, 7000);
      if (vr.ok) {
        const vj = await vr.json();
        vItems.push(...(vj.items || []));
      }
    } catch (e) {}
  }

  const now = Date.now();
  const all = [];
  for (const v of vItems) {
    const dur = parseIsoDurationSec(v.contentDetails && v.contentDetails.duration);
    // Tech/Movie/Updates channels also make 1-12 min explainers we can turn into crisp Shorts!
    const maxDur = (catKey === "facts") ? 210 : 720;
    if (dur < 12 || dur > maxDur) continue;
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
      catKey,
      views,
      dur,
      ageDays: Math.round(ageH / 24),
      velScore: views / Math.pow(ageH, 0.85),
      url: `https://www.youtube.com/watch?v=${v.id}`,
    });
  }

  // Outlier Viral Score (views / channel median)
  const byCh = new Map();
  for (const x of all) {
    const k = x.handle || x.channel;
    if (!byCh.has(k)) byCh.set(k, []);
    byCh.get(k).push(x.views);
  }
  const chMed = new Map();
  for (const [k, arr] of byCh.entries()) {
    arr.sort((a, b) => a - b);
    chMed.set(k, Math.max(1000, arr[Math.floor(arr.length / 2)] || 1000));
  }
  for (const x of all) {
    const med = chMed.get(x.handle || x.channel) || 10000;
    const mult = Math.max(0.2, x.views / med);
    x.outlierMult = Number(mult.toFixed(1));
    x.viralRating = Math.min(9.9, Math.max(5.0, Number((5.2 + Math.log2(mult + 0.5) * 1.85).toFixed(1))));
    x.score = x.velScore * Math.min(4.0, Math.sqrt(mult));
  }

  // Prefer last 45 days; filter out already seen/used videos on Refresh!
  const recent = all.filter(x => x.ageDays <= 45);
  const basePool = recent.length >= 5 ? recent : all;
  const freshPool = basePool.filter(x => !seenSet.has(x.id));
  const recycled = freshPool.length < 3 && basePool.length > 0;
  const pool = recycled ? [...basePool] : [...freshPool];
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
  return { items: picked, recycled };
}

async function showTrendCategoryMenu(env, chatId, editMsgId = null) {
  const txt =
    "🔥 /trends — Kis Category Ke Viral Topics Scan Karun?\n\n" +
    "Har category me top Indian channels scan honge aur 🔄 Refresh dabane par hamesha 5 NAYE topics milenge (purane repeat nahi honge!):";
  const kb = {
    inline_keyboard: [
      [{ text: "🧠 Facts & Science", callback_data: "tr:cat:facts" }, { text: "📱 Tech & Gadgets", callback_data: "tr:cat:tech" }],
      [{ text: "🎬 Movies & Reviews", callback_data: "tr:cat:movies" }, { text: "🚀 YT / IG / AI Updates", callback_data: "tr:cat:updates" }],
      [{ text: "🌍 Mix All (Top Viral)", callback_data: "tr:cat:mix" }],
    ],
  };
  if (editMsgId) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: editMsgId, text: txt, reply_markup: kb });
  } else {
    await tgApi(env, "sendMessage", { chat_id: chatId, text: txt, reply_markup: kb });
  }
}

async function runTrendsForCategory(env, chatId, catKey = "facts", isRefresh = false, editMsgId = null) {
  const cat = TREND_CATEGORIES[catKey] || TREND_CATEGORIES.facts;
  const waitTxt = `🔥 ${cat.label} ke ${isRefresh ? "NAYE viral topics" : "top viral videos"} scan kar raha hoon (~5 sec)...`;
  let waitMsgId = editMsgId;
  if (waitMsgId) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsgId, text: waitTxt });
  } else {
    const waitRes = await tgApi(env, "sendMessage", { chat_id: chatId, text: waitTxt });
    waitMsgId = waitRes.ok ? ((await waitRes.json()).result || {}).message_id : null;
  }

  const prev = await readGhJson(env, TRENDS_CACHE_PATH, { items: [], seenByCat: {} });
  const seenByCat = (prev.data && prev.data.seenByCat && typeof prev.data.seenByCat === "object") ? { ...prev.data.seenByCat } : {};
  const prevSeen = Array.isArray(seenByCat[catKey]) ? seenByCat[catKey] : [];
  const prevIds = (prev.data && Array.isArray(prev.data.items) && prev.data.catKey === catKey)
    ? prev.data.items.map(x => x.id).filter(Boolean) : [];
  const excludeIds = isRefresh ? Array.from(new Set([...prevSeen, ...prevIds])) : prevSeen;

  const scan = await scanCompetitorTrends(env, catKey, excludeIds);
  const trends = scan.items || [];
  if (!trends.length) {
    const errTxt = `❌ ${cat.label} me abhi koi trending video nahi mili (YOUTUBE_KEY quota check karein).`;
    if (waitMsgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsgId, text: errTxt });
    else await tgReply(env.TG_TOKEN, chatId, errTxt, true);
    return;
  }

  const newIds = trends.map(v => v.id);
  seenByCat[catKey] = scan.recycled
    ? newIds
    : Array.from(new Set([...excludeIds, ...newIds])).slice(-50);

  await writeGhJson(env, TRENDS_CACHE_PATH, { items: trends, catKey, seenByCat, ts: Date.now() }, prev.sha, `trends ${catKey}`);

  const lines = [
    `🔥 ${cat.label} — Top 5 ${isRefresh ? "NAYE " : ""}Viral Topics${scan.recycled ? " (Pool reset ✓)" : ""}:\n`,
  ];
  trends.forEach((v, i) => {
    const badge = v.outlierMult ? ` • 🔥 ${v.outlierMult}x (${v.viralRating}/10)` : "";
    lines.push(`${i + 1}️⃣ ${v.title.slice(0, 72)}\n   📺 ${v.channel} • 👁 ${fmtViews(v.views)} (${v.ageDays}d)${badge}\n   🔗 ${v.url}`);
  });
  lines.push("\n👇 Number tap karo (100% original Hindi script + exact visuals hints banenge — approval ke baad hi video banegi):");

  const kb = {
    inline_keyboard: [
      trends.slice(0, 3).map((_, i) => ({ text: `${i + 1}️⃣ Script Banao`, callback_data: `tr:pick:${i}` })),
      trends.slice(3, 5).map((_, i) => ({ text: `${i + 4}️⃣ Script Banao`, callback_data: `tr:pick:${i + 3}` })).concat([{ text: "🔄 Naye 5 (Refresh)", callback_data: `tr:ref:${catKey}` }]),
      [{ text: "📂 Category Badlo", callback_data: "tr:menu" }],
    ],
  };
  if (waitMsgId) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsgId, text: lines.join("\n"), disable_web_page_preview: true, reply_markup: kb });
  } else {
    await tgApi(env, "sendMessage", { chat_id: chatId, text: lines.join("\n"), disable_web_page_preview: true, reply_markup: kb });
  }
}

async function handleTrendsCommand(env, chatId) {
  if (!env.YOUTUBE_KEY || (!env.GEMINI_KEY && !env.GROQ_KEY)) {
    await tgReply(env.TG_TOKEN, chatId,
      "🔑 /trends chalane ke liye Cloudflare Worker (vg-bots) me YOUTUBE_KEY aur GEMINI_KEY/GROQ_KEY honi chahiye.", true);
    return;
  }
  await showTrendCategoryMenu(env, chatId);
}

function getGeminiKeys(env) {
  return String(env.GEMINI_KEY || "").split(",").map(s => s.trim()).filter(Boolean);
}

function getGroqKeys(env) {
  return String(env.GROQ_KEY || "").split(",").map(s => s.trim()).filter(Boolean);
}

function sleepMs(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function fetchWithTimeout(url, opts = {}, ms = 12000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort("timeout"), ms);
  try {
    return await fetch(url, { ...opts, signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
}

async function discoverGeminiModels(gKey) {
  const defaults = [
    "gemini-3.8-flash",
    "gemini-3.8-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.7-flash-lite",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
  ];
  if (!gKey) return defaults;
  try {
    const r = await fetchWithTimeout(`https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(gKey)}`, {}, 3500);
    if (!r.ok) return defaults;
    const j = await r.json();
    const avail = (j.models || [])
      .filter(m => Array.isArray(m.supportedGenerationMethods) && m.supportedGenerationMethods.includes("generateContent"))
      .map(m => String(m.name || "").replace(/^models\//, ""))
      .filter(n => /gemini/i.test(n) && /flash/i.test(n) && !/(tts|audio|image|embedding|live|robotics|computer|customtools)/i.test(n));
    avail.sort((a, b) => {
      const va = parseFloat((a.match(/gemini-(\d+(?:\.\d+)?)/i) || [0, "0"])[1]);
      const vb = parseFloat((b.match(/gemini-(\d+(?:\.\d+)?)/i) || [0, "0"])[1]);
      if (vb !== va) return vb - va;
      return (/lite/i.test(a) ? 1 : 0) - (/lite/i.test(b) ? 1 : 0);
    });
    // v3.94: Interleave standard Flash + low-congestion Flash-Lite so 503 on heavy Flash jumps to Lite!
    const std = avail.filter(m => !/lite/i.test(m));
    const lite = avail.filter(m => /lite/i.test(m));
    const interleaved = [];
    const maxLen = Math.max(std.length, lite.length);
    for (let i = 0; i < maxLen; i++) {
      if (std[i]) interleaved.push(std[i]);
      if (lite[i]) interleaved.push(lite[i]);
    }
    const out = [];
    for (const m of interleaved.concat(defaults)) if (m && !out.includes(m)) out.push(m);
    return out.slice(0, 6);
  } catch (e) {
    return defaults;
  }
}

async function fetchYouTubeTranscriptText(videoId) {
  try {
    const page = await fetchWithTimeout(`https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`, {
      headers: { "Accept-Language": "hi-IN,hi;q=0.9,en;q=0.8", "User-Agent": "Mozilla/5.0" },
    }, 4500);
    if (!page.ok) return "";
    const html = await page.text();
    const m = html.match(/"captionTracks":(\[[\s\S]*?\])/);
    if (!m) return "";
    const tracks = JSON.parse(m[1]);
    if (!Array.isArray(tracks) || !tracks.length) return "";
    const pick = tracks.find(t => /^hi/i.test(t.languageCode || "")) || tracks.find(t => /^en/i.test(t.languageCode || "")) || tracks[0];
    if (!pick || !pick.baseUrl) return "";
    const tr = await fetchWithTimeout(pick.baseUrl, {}, 3500);
    if (!tr.ok) return "";
    const xml = await tr.text();
    return xml.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
      .replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, " ").trim().slice(0, 2200);
  } catch (e) {
    return "";
  }
}

async function discoverGroqModels(gk) {
  const defaults = [
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
  ];
  if (!gk) return defaults;
  try {
    const r = await fetchWithTimeout("https://api.groq.com/openai/v1/models", {
      headers: { "Authorization": `Bearer ${gk}` },
    }, 3000);
    if (!r.ok) return defaults;
    const j = await r.json();
    const ids = (j.data || [])
      .map(m => String(m && m.id || "").trim())
      .filter(id => id && !/(whisper|tts|audio|guard|safeguard|embed|orpheus|playai|vision|distil-whisper)/i.test(id));
    if (!ids.length) return defaults;
    const preferred = [
      "qwen/qwen3.8-27b",
      "qwen/qwen3.6-27b",
      "openai/gpt-oss-120b",
      "openai/gpt-oss-20b",
      "moonshotai/kimi-k2-instruct",
    ];
    const ranked = [];
    for (const p of preferred) {
      if (ids.includes(p)) ranked.push(p);
    }
    for (const id of ids) {
      if (!ranked.includes(id) && /(qwen3|gpt-oss|llama-4|kimi|deepseek|mistral)/i.test(id)) {
        ranked.push(id);
      }
    }
    return (ranked.length ? ranked : ids).slice(0, 5);
  } catch (e) {
    return defaults;
  }
}

async function callGroqTrendScript(env, prompt, hasTranscript, errs, deadlineTs = 0) {
  const groqKeys = getGroqKeys(env);
  if (!groqKeys.length) {
    errs.push("groq: GROQ_KEY missing");
    return null;
  }
  const groqModels = await discoverGroqModels(groqKeys[0]);
  for (const gk of groqKeys.slice(0, 2)) {
    for (const gm of groqModels) {
      if (deadlineTs && Date.now() > deadlineTs) break;
      const baseBody = {
        model: gm,
        temperature: 0.7,
        max_completion_tokens: 2600,
        messages: [
          { role: "system", content: "You are India's #1 viral Hindi YouTube Shorts Director for The Viral Gyaan. Follow the exact requested output format with VISUAL_REFS: and SCRIPT: sections." },
          { role: "user", content: prompt },
        ],
      };
      if (/^qwen\/qwen3/i.test(gm)) baseBody.reasoning_effort = "none";
      else if (/gpt-oss/i.test(gm)) baseBody.reasoning_effort = "low";

      const tryCall = async (payload) => fetchWithTimeout("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${gk}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }, 11000);

      try {
        let r = await tryCall(baseBody);
        // If a model rejects reasoning_effort with 400, retry cleanly without it
        if (r.status === 400 && baseBody.reasoning_effort) {
          const cleanBody = { ...baseBody };
          delete cleanBody.reasoning_effort;
          r = await tryCall(cleanBody);
        }
        if (r.ok) {
          const j = await r.json();
          const out = (j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content || "").trim();
          if (out && out.includes("MODE:")) {
            return { text: out, mode: hasTranscript ? "groq_transcript" : "groq_topic", model: `groq/${gm}` };
          }
          if (out) {
            return { text: out, mode: hasTranscript ? "groq_transcript" : "groq_topic", model: `groq/${gm}` };
          }
          errs.push(`groq/${gm}: empty`);
        } else {
          errs.push(`groq/${gm}: ${r.status}`);
          if (r.status === 404) continue;
        }
      } catch (e) {
        errs.push(`groq/${gm}: ${String(e).slice(0, 32)}`);
      }
    }
  }
  return null;
}

async function callGeminiTrendScript(env, video, rewrite = false) {
  const t0 = Date.now();
  const keys = getGeminiKeys(env);
  const groqKeys = getGroqKeys(env);
  if (!keys.length && !groqKeys.length) return { text: "", error: "GEMINI_KEY aur GROQ_KEY dono missing hain" };

  const basePrompt = `You are India's #1 viral Hindi YouTube Shorts Director for "The Viral Gyaan".
TASK:
1) Study this reference viral YouTube Short. Ignore competitor editing — focus ONLY on the factual topic and WHAT REAL FOOTAGES, IMAGES, OBJECTS, PEOPLE, AND SCENES best explain it.
2) Write a 100% ORIGINAL, 100% FACTUAL Hindi YouTube Short script on this same viral topic (NEVER copy/translate, and NEVER invent fake app features, fake updates, or fake statistics not in the reference info — use a fresh, gripping hook${rewrite ? " with a COMPLETELY DIFFERENT opening hook and angle than before" : ""}).
3) For every script line, put camera-exact English visual references after "||" (3-5 simple English words — NO "reconstruction", "reenactment", "examination", "interview", "chart"; NO "[YT]"/"[X]" tags).
${(TREND_CATEGORIES[(video && video.catKey) || "facts"] || TREND_CATEGORIES.facts).visualRule}

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

  const errs = [];
  let models = [];
  let vidFailedModel = "";

  // Step 1: Fast 9s-bounded native YouTube URL video watch (1 top model only -> safe inside CF 30s!)
  if (keys.length) {
    const gKey = keys[0];
    models = await discoverGeminiModels(gKey);
    const vidModel = models.find(m => !/lite/i.test(m)) || models[0];
    if (vidModel) {
      try {
        const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${vidModel}:generateContent?key=${encodeURIComponent(gKey)}`;
        const r = await fetchWithTimeout(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ role: "user", parts: [{ fileData: { fileUri: video.url, mimeType: "video/*" } }, { text: basePrompt }] }],
          }),
        }, 9000);
        if (r.ok) {
          const j = await r.json();
          const out = j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts
            ? j.candidates[0].content.parts.map(p => p.text || "").join("\n").trim() : "";
          if (out && out.includes("MODE:")) return { text: out, mode: "video", model: vidModel };
        } else {
          errs.push(`${vidModel}(vid): ${r.status}`);
          if (r.status === 503 || r.status === 429) vidFailedModel = vidModel;
        }
      } catch (e) {
        errs.push(`${vidModel}(vid): ${String(e).slice(0, 32)}`);
      }
    }
  }

  // Step 2: Fast YouTube Transcript/Captions + Topic fallback (v3.94: Flash-Lite priority + key rotation + time budget!)
  const transcript = await fetchYouTubeTranscriptText(video.id);
  const ctxBlock = transcript
    ? `Reference viral Short title: "${video.title}" (Channel: ${video.channel}).\nSpoken transcript (DO NOT copy wording — extract only facts & visuals):\n${transcript}`
    : `Reference viral Short title: "${video.title}" (Channel: ${video.channel}).`;
  const fbPrompt = basePrompt + "\n\nREFERENCE INFO:\n" + ctxBlock;

  if (keys.length) {
    // Prioritize Flash-Lite & non-failed models first so 503 on top Flash doesn't block fallback
    const liteModels = models.filter(m => /lite/i.test(m));
    const otherStd = models.filter(m => !/lite/i.test(m) && m !== vidFailedModel);
    const textModels = [...liteModels.slice(0, 2), ...otherStd.slice(0, 2), ...(vidFailedModel ? [vidFailedModel] : [])]
      .filter((m, idx, arr) => m && arr.indexOf(m) === idx)
      .slice(0, 4);

    // Reserve at least ~8s for Groq backup if GROQ_KEY is available
    const geminiDeadlineMs = groqKeys.length ? 16000 : 24000;
    let tried503 = false;

    for (const model of textModels) {
      for (const k of keys.slice(0, 2)) {
        if (Date.now() - t0 > geminiDeadlineMs) break;
        try {
          if (tried503) {
            await sleepMs(450);
            tried503 = false;
          }
          const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(k)}`;
          const r2 = await fetchWithTimeout(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: fbPrompt }] }] }),
          }, 6500);
          if (r2.ok) {
            const j2 = await r2.json();
            const out2 = j2.candidates && j2.candidates[0] && j2.candidates[0].content && j2.candidates[0].content.parts
              ? j2.candidates[0].content.parts.map(p => p.text || "").join("\n").trim() : "";
            if (out2) return { text: out2, mode: transcript ? "transcript" : "topic", model };
          } else {
            errs.push(`${model}: ${r2.status}`);
            if (r2.status === 503 || r2.status === 429) tried503 = true;
            // If non-transient (404/400), no point retrying same model on second key
            if (r2.status === 404 || r2.status === 400) break;
          }
        } catch (e) {
          errs.push(`${model}: ${String(e).slice(0, 32)}`);
        }
      }
      if (Date.now() - t0 > geminiDeadlineMs) break;
    }
  }

  // Step 3 (v4.01): Instant Groq Zero-Downtime Backup (auto-discovered active models + non-empty reasoning guard!)
  if (groqKeys.length) {
    const groqRes = await callGroqTrendScript(env, fbPrompt, Boolean(transcript), errs, t0 + 27500);
    if (groqRes && groqRes.text) return groqRes;
  }

  const gemErrs = errs.filter(e => !e.startsWith("groq")).slice(0, 4);
  const grqErrs = errs.filter(e => e.startsWith("groq")).slice(0, 4);
  const mergedErrs = [...gemErrs, ...grqErrs];
  return { text: "", error: (mergedErrs.length ? mergedErrs : errs.slice(0, 6)).join(" | ") };
}

function parseTrendGeminiOutput(raw) {
  let clean = String(raw || "").replace(/```[a-z]*\n?/gi, "").replace(/```/g, "").trim();
  // v3.98 FIX: Join accidental newlines before punctuation or '||' (prevents empty '।' lines that trigger voice glitches!)
  clean = clean.replace(/\r\n/g, "\n").replace(/\n+\s*([।.!?]+\s*\|\||\|\|)/g, " $1");
  const idx = clean.indexOf("SCRIPT:");
  if (idx === -1) return { refs: "", script: clean };
  const refs = clean.slice(0, idx).replace(/VISUAL_REFS:/i, "").trim();
  const script = clean.slice(idx + 7).trim();
  return { refs, script };
}

async function handleTrendCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  const msgId = cq.message ? cq.message.message_id : null;
  let statusMsg = null;
  try {
    await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
    if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
    const data = cq.data || "";

    if (data === "tr:menu") { await showTrendCategoryMenu(env, chatId, msgId); return; }
    if (data.startsWith("tr:cat:")) {
      const ck = data.split(":")[2] || "facts";
      await runTrendsForCategory(env, chatId, ck, false, msgId);
      return;
    }
    if (data === "tr:ref" || data.startsWith("tr:ref:")) {
      const ck = data.includes(":ref:") ? (data.split(":")[2] || "facts") : "facts";
      await runTrendsForCategory(env, chatId, ck, true, msgId);
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
        ? "🚀 Approved! SHORT video cloud par shuru ho gayi hai!\nBante hi video + Cover + Story + Auto-Publish buttons yahin aayenge."
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
      text: `👀 Gemini asli YouTube video dekh kar visual references aur ${rewrite ? "naya angle" : "original"} Hindi script likh raha hai (~10-15 sec)...\n🔗 ${video.url}`,
      disable_web_page_preview: true,
    });
    statusMsg = statusRes.ok ? (await statusRes.json()).result : null;

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
        : (gen.mode === "groq_transcript"
          ? `⚡ Gemini busy (503) tha — Groq backup ne YouTube transcript se original script + visual hints banaye ✓ (${gen.model})`
          : (gen.mode === "groq_topic"
            ? `⚡ Gemini busy (503) tha — Groq backup ne viral topic se script banayi (${gen.model})\n⚠️ Note: Is video ka transcript nahi mila tha (sirf title se bani) — publish se pehle facts zaroor check kar lein!`
            : `⚡ Viral topic se script banayi (${gen.model})\n⚠️ Note: Is video ka transcript nahi mila tha (sirf title se bani) — publish se pehle facts zaroor check kar lein!`)));
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
  } catch (err) {
    const errMsg = `❌ /trends error: ${String(err).slice(0, 220)}\n(Dobara 🔥 /trends try karo)`;
    if (statusMsg) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: statusMsg.message_id, text: errMsg });
    else if (chatId) await tgReply(env.TG_TOKEN, chatId, errMsg, true);
  }
}

// ---------------- v3.93: Rollback Confirmation Guard ----------------
async function handleRollbackConfirm(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  const msgId = cq.message ? cq.message.message_id : null;
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  if (cq.data === "rb:go") {
    const ok = await dispatchGH(env, "apply_update.yml", { action: "rollback", file_id: "" });
    const txt = ok ? "⏪ Pichhla version (/purana) cloud par restore kar raha hoon (~30 sec)..." : "❌ Rollback trigger fail ho gaya.";
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: txt });
  } else {
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "✅ Rollback cancel — current version safe hai." });
  }
}

// ---------------- v3.93: Post-Approval Auto-Publish (YouTube Unlisted + FB Page + IG Reels + Cover + Story) ----------------
const PUB_PATH = "/contents/seekha/pending_publish.json";
const GRAPH_VER = "v27.0";

async function registerPublishCard(env, payload) {
  const chatId = String(payload.chat_id || env.ALLOWED_CHAT_ID || "");
  if (!chatId) return;
  const id = Date.now().toString(36).slice(-6);
  const cur = await readGhJson(env, PUB_PATH, {});
  const store = (cur.data && typeof cur.data === "object") ? { ...cur.data } : {};
  const keys = Object.keys(store);
  if (keys.length >= 10) {
    keys.sort((a, b) => (store[a].ts || 0) - (store[b].ts || 0));
    for (const oldK of keys.slice(0, keys.length - 9)) delete store[oldK];
  }
  const mode = String(payload.mode || "SHORT").toUpperCase();
  store[id] = {
    id, ts: Date.now(), mode,
    category: payload.category || "general",
    video_url: payload.video_url || "",
    tg_file_id: payload.tg_file_id || "",
    cover_url: payload.cover_url || "",
    story_url: payload.story_url || "",
    cover_tg_file_id: payload.cover_tg_file_id || "",
    story_tg_file_id: payload.story_tg_file_id || "",
    title: payload.title || "The Viral Gyaan",
    description: payload.description || "",
    ig_caption: payload.ig_caption || payload.description || "",
    tags: payload.tags || "",
  };
  await writeGhJson(env, PUB_PATH, store, cur.sha, `register publish ${id}`);

  const isLong = mode === "LONG";
  const kb = isLong ? {
    inline_keyboard: [
      [{ text: "🚀 YT PUBLIC + FB Page", callback_data: `pub:${id}:all_pub` }],
      [{ text: "✅ YT Unlisted + FB Page", callback_data: `pub:${id}:all` }],
      [{ text: "▶️ YT PUBLIC", callback_data: `pub:${id}:yt_pub` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf Facebook Page", callback_data: `pub:${id}:meta` }, { text: "❌ Skip", callback_data: `pub:${id}:skip` }],
    ],
  } : {
    inline_keyboard: [
      [{ text: "🚀 Sab Par PUBLIC (YT + FB + IG + Story)", callback_data: `pub:${id}:all_pub` }],
      [{ text: "✅ Sab Par (YT Unlisted + FB + IG + Story)", callback_data: `pub:${id}:all` }],
      [{ text: "▶️ YT PUBLIC", callback_data: `pub:${id}:yt_pub` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf FB + IG + Story", callback_data: `pub:${id}:meta` }, { text: "❌ Skip", callback_data: `pub:${id}:skip` }],
    ],
  };

  const cardText =
    `🚀 Auto-Publish Ready! (${isLong ? "LONG 16:9" : "SHORT 9:16"})\n\n` +
    `🎬 Title: ${store[id].title.slice(0, 95)}\n` +
    `📝 Desc: ${store[id].description.slice(0, 260)}\n\n` +
    `👇 Kahan aur kaise publish karun? (YouTube PUBLIC ya UNLISTED dono chalu hain!)`;
  await tgApi(env, "sendMessage", { chat_id: chatId, text: cardText.slice(0, 3900), reply_markup: kb });
}

const WORKER_PUBLIC_ORIGIN = "https://vg-bots.laxmandan2489.workers.dev";

function buildMetaMediaUrl(tgFileId, fallbackUrl, ext, preferProxyForVideo = true) {
  const cleanExt = ext === "jpg" ? "jpg" : "mp4";
  // v4.04: For Video (MP4), prioritize Verified Full-HD Master proxy FIRST (0% compression + supports 50-200MB Long Videos!)
  if (cleanExt === "mp4" && preferProxyForVideo && fallbackUrl) {
    return `${WORKER_PUBLIC_ORIGIN}/media/proxy?u=${encodeURIComponent(fallbackUrl)}&t=mp4`;
  }
  if (tgFileId) {
    const fbQ = fallbackUrl ? `?fb=${encodeURIComponent(fallbackUrl)}` : "";
    return `${WORKER_PUBLIC_ORIGIN}/media/tg/${encodeURIComponent(tgFileId)}.${cleanExt}${fbQ}`;
  }
  if (fallbackUrl) {
    return `${WORKER_PUBLIC_ORIGIN}/media/proxy?u=${encodeURIComponent(fallbackUrl)}&t=${cleanExt}`;
  }
  return "";
}

async function handleTgMediaBridge(env, pathname, fallbackUrl = "", headOnly = false) {
  const token = (env.TG_TOKEN || "").trim();
  const raw = pathname.slice("/media/tg/".length);
  const dot = raw.lastIndexOf(".");
  const fid = decodeURIComponent(dot > 0 ? raw.slice(0, dot) : raw).trim();
  const ext = (dot > 0 ? raw.slice(dot + 1) : "jpg").toLowerCase();
  const ctype = ext === "mp4" ? "video/mp4" : "image/jpeg";
  if (token && fid && fid.length >= 10) {
    try {
      const gf = await fetchWithTimeout(`https://api.telegram.org/bot${token}/getFile?file_id=${encodeURIComponent(fid)}`, {}, 8000);
      const gj = await gf.json();
      const fpath = gj && gj.ok && gj.result && gj.result.file_path;
      if (fpath) {
        const upstream = await fetch(`https://api.telegram.org/file/bot${token}/${fpath}`);
        if (upstream.ok) {
          const headers = new Headers({
            "Content-Type": ctype,
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
          });
          const cl = upstream.headers.get("Content-Length");
          if (cl) headers.set("Content-Length", cl);
          return new Response(headOnly ? null : upstream.body, { status: 200, headers });
        }
      }
    } catch (e) {
      // Fall through to fallbackUrl proxy if Telegram getFile >20MB fails
    }
  }
  if (fallbackUrl && /^https?:\/\//i.test(fallbackUrl)) {
    return handleProxyMediaBridge(fallbackUrl, ext, headOnly);
  }
  return new Response("tg file unavailable", { status: 404 });
}

async function handleProxyMediaBridge(rawUrl, typeHint, headOnly = false) {
  const target = String(rawUrl || "").trim();
  if (!/^https?:\/\//i.test(target)) return new Response("bad url", { status: 400 });
  const ctype = typeHint === "jpg" ? "image/jpeg" : "video/mp4";
  try {
    const upstream = await fetch(target, {
      headers: {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
        "Accept": "*/*",
      },
      redirect: "follow",
    });
    if (!upstream.ok) return new Response("upstream fail", { status: 502 });
    const headers = new Headers({
      "Content-Type": ctype,
      "Accept-Ranges": "bytes",
      "Cache-Control": "public, max-age=3600",
    });
    const cl = upstream.headers.get("Content-Length");
    if (cl) headers.set("Content-Length", cl);
    return new Response(headOnly ? null : upstream.body, { status: 200, headers });
  } catch (e) {
    return new Response("proxy bridge err", { status: 502 });
  }
}

async function getFacebookPageToken(systemToken, pageId) {
  // v4.04 FIX: Try BOTH /{pageId}?fields=access_token AND /me/accounts (required for New Pages Experience System Users!)
  try {
    const r = await fetchWithTimeout(
      `https://graph.facebook.com/${GRAPH_VER}/${pageId}?fields=access_token&access_token=${encodeURIComponent(systemToken)}`,
      {},
      8000
    );
    if (r.ok) {
      const j = await r.json();
      if (j && j.access_token) return String(j.access_token).trim();
    }
  } catch (e) {}
  try {
    const r2 = await fetchWithTimeout(
      `https://graph.facebook.com/${GRAPH_VER}/me/accounts?fields=id,name,access_token&limit=50&access_token=${encodeURIComponent(systemToken)}`,
      {},
      8000
    );
    if (r2.ok) {
      const j2 = await r2.json();
      const hit = (j2.data || []).find(p => String(p.id) === String(pageId));
      if (hit && hit.access_token) return String(hit.access_token).trim();
    }
  } catch (e) {}
  return systemToken;
}

async function publishFacebookPage(env, item) {
  const sysToken = (env.META_ACCESS_TOKEN || "").trim();
  const pageId = (env.FB_PAGE_ID || "").trim();
  if (!sysToken || !pageId) return { ok: false, msg: "⚠️ FB skip: Cloudflare me META_ACCESS_TOKEN aur FB_PAGE_ID add karo." };
  try {
    const pageToken = await getFacebookPageToken(sysToken, pageId);
    const mediaUrl = buildMetaMediaUrl(item.mode === "SHORT" ? item.tg_file_id : "", item.video_url, "mp4") || item.video_url;

    if (item.mode === "LONG") {
      const r = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/videos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_url: mediaUrl, title: item.title, description: item.ig_caption, access_token: pageToken }),
      }, 22000);
      const j = await r.json();
      if (r.ok && j.id) return { ok: true, msg: `✅ Facebook Video Published (ID: ${j.id})` };
      return { ok: false, msg: `❌ FB Video error: ${(j.error && j.error.message) || r.status}` };
    }
    // SHORT -> Official Facebook Page Reels 3-step URL flow (with Page Access Token!)
    const s1 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/video_reels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_phase: "start", access_token: pageToken }),
    }, 12000);
    const j1 = await s1.json();
    if (!s1.ok || !j1.video_id) return { ok: false, msg: `❌ FB Reel start fail: ${(j1.error && j1.error.message) || s1.status}` };

    const s2 = await fetchWithTimeout(`https://rupload.facebook.com/video-upload/${GRAPH_VER}/${j1.video_id}`, {
      method: "POST",
      headers: { Authorization: `OAuth ${pageToken}`, file_url: mediaUrl },
    }, 18000);
    if (!s2.ok) {
      const t2 = await s2.text();
      return { ok: false, msg: `❌ FB Reel upload fail: ${t2.slice(0, 120)}` };
    }

    const s3 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/video_reels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_phase: "finish",
        video_id: j1.video_id,
        video_state: "PUBLISHED",
        description: item.ig_caption || item.title,
        access_token: pageToken,
      }),
    }, 12000);
    const j3 = await s3.json();
    if (s3.ok && (j3.success || j3.post_id)) return { ok: true, msg: `✅ Facebook Page Reel Published!` };
    return { ok: false, msg: `❌ FB Reel finish fail: ${(j3.error && j3.error.message) || s3.status}` };
  } catch (e) {
    return { ok: false, msg: `❌ FB error: ${String(e).slice(0, 120)}` };
  }
}

async function publishInstagramReelAndStory(env, item) {
  const token = (env.META_ACCESS_TOKEN || "").trim();
  const igId = (env.IG_USER_ID || "").trim();
  if (!token || !igId) return { ok: false, msg: "⚠️ IG skip: Cloudflare me META_ACCESS_TOKEN aur IG_USER_ID add karo." };
  const notes = [];
  let pendingContainer = null;

  // 1) Create & Publish Designer Instagram Story via Cloudflare clean JPEG Media Bridge
  const storyBridgeUrl = buildMetaMediaUrl(item.story_tg_file_id, item.story_url, "jpg");
  if (storyBridgeUrl) {
    try {
      const st1 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ media_type: "STORIES", image_url: storyBridgeUrl, access_token: token }),
      }, 10000);
      const sj1 = await st1.json();
      if (st1.ok && sj1.id) {
        await new Promise(r => setTimeout(r, 2500));
        const st2 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media_publish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ creation_id: sj1.id, access_token: token }),
        }, 10000);
        const sj2 = await st2.json();
        notes.push(st2.ok && sj2.id ? "✅ IG Designer Story Published!" : `⚠️ IG Story pending/err: ${(sj2.error && sj2.error.message) || st2.status}`);
      } else {
        notes.push(`⚠️ IG Story fail: ${(sj1.error && sj1.error.message) || st1.status}`);
      }
    } catch (e) {
      notes.push(`⚠️ IG Story error: ${String(e).slice(0, 80)}`);
    }
  }

  // 2) Create & Poll Instagram Reel via Cloudflare clean MP4 + Cover JPEG Media Bridge
  const videoBridgeUrl = buildMetaMediaUrl(item.tg_file_id, item.video_url, "mp4") || item.video_url;
  const coverBridgeUrl = buildMetaMediaUrl(item.cover_tg_file_id, item.cover_url, "jpg");

  const tryCreateAndPollReel = async (includeCover) => {
    const reelBody = {
      media_type: "REELS",
      video_url: videoBridgeUrl,
      caption: (item.ig_caption || item.title).slice(0, 2100),
      share_to_feed: true,
      access_token: token,
    };
    if (includeCover && coverBridgeUrl) reelBody.cover_url = coverBridgeUrl;
    const r1 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reelBody),
    }, 12000);
    const j1 = await r1.json();
    if (!r1.ok || !j1.id) {
      return { status: "create_fail", err: (j1.error && j1.error.message) || String(r1.status) };
    }
    const cid = j1.id;
    for (let attempt = 0; attempt < 4; attempt++) {
      await new Promise(r => setTimeout(r, 3500));
      const st = await fetchWithTimeout(
        `https://graph.facebook.com/${GRAPH_VER}/${cid}?fields=status_code,status&access_token=${encodeURIComponent(token)}`,
        {},
        8000
      );
      if (st.ok) {
        const sj = await st.json();
        if (sj.status_code === "FINISHED") return { status: "ready", cid };
        if (sj.status_code === "ERROR") {
          return { status: "meta_error", err: sj.status || "Meta processing error" };
        }
      }
    }
    return { status: "pending", cid };
  };

  try {
    let res = await tryCreateAndPollReel(true);
    // If failed with cover_url, retry once cleanly without cover_url
    if ((res.status === "create_fail" || res.status === "meta_error") && coverBridgeUrl) {
      res = await tryCreateAndPollReel(false);
    }
    if (res.status === "ready") {
      const pub = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: res.cid, access_token: token }),
      }, 10000);
      const pj = await pub.json();
      notes.push(pub.ok && pj.id ? "✅ Instagram Reel (+ Cover) Published!" : `❌ IG Publish fail: ${(pj.error && pj.error.message) || pub.status}`);
    } else if (res.status === "pending") {
      pendingContainer = res.cid;
      notes.push("⏳ Instagram video abhi Meta par process ho raha hai — 15 sec baad neeche '🔄 Complete IG Reel Publish' dabao!");
    } else {
      notes.push(`❌ IG Reel fail: ${res.err}`);
      return { ok: false, msg: notes.join("\n") };
    }
  } catch (e) {
    notes.push(`❌ IG Reel error: ${String(e).slice(0, 100)}`);
  }
  return { ok: !pendingContainer, msg: notes.join("\n"), pendingContainer };
}

async function handlePublishCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  const msgId = cq.message ? cq.message.message_id : null;
  try {
    await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
    if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
    const parts = (cq.data || "").split(":");
    const id = parts[1] || "";
    const action = parts[2] || "";

    if (action === "skip") {
      if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "⏭️ Auto-Publish skip kar diya (video + Cover + Story saved hain — baad me /republish se kabhi bhi daal sakte ho)." });
      return;
    }
    if (action === "card") {
      const storeC = await readGhJson(env, PUB_PATH, {});
      const itC = storeC.data && storeC.data[id];
      if (!itC) {
        await tgReply(env.TG_TOKEN, chatId, "⚠️ Ye video vault me nahi mila (aakhri 10 videos saved rehte hain).", false);
        return;
      }
      await sendPublishCardForItem(env, chatId, itC);
      return;
    }

    // Complete delayed IG Reel container publish
    if (action === "igfin") {
      const cid = parts[3] || "";
      const token = (env.META_ACCESS_TOKEN || "").trim();
      const igId = (env.IG_USER_ID || "").trim();
      const pub = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: cid, access_token: token }),
      }, 12000);
      const pj = await pub.json();
      const txt = pub.ok && pj.id
        ? "✅ Instagram Reel (+ Cover) Published!"
        : `⏳ Abhi bhi process ho raha hai ya error: ${(pj.error && pj.error.message) || pub.status}`;
      await tgReply(env.TG_TOKEN, chatId, txt, false);
      return;
    }

    const store = await readGhJson(env, PUB_PATH, {});
    const item = store.data && store.data[id];
    if (!item || (!item.video_url && !item.tg_file_id)) {
      if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "⚠️ Ye publish card purana ho gaya (sirf aakhri 5 videos saved rehte hain)." });
      return;
    }

    if (msgId) {
      await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: `⏳ Publishing shuru (${action.toUpperCase()})...\n🎬 ${item.title.slice(0, 70)}` });
    }

    const report = [`📣 Publish Report — ${item.title.slice(0, 65)}`];
    let pendingIgCid = null;

    const doYt = (action === "yt" || action === "all" || action === "yt_pub" || action === "all_pub");
    const doMeta = (action === "meta" || action === "all" || action === "all_pub");
    const ytPrivacy = (action === "yt_pub" || action === "all_pub") ? "public" : "unlisted";

    if (doYt) {
      const ytVideoUrl = item.video_url
        ? (item.tg_file_id ? `${item.video_url}#vg_tg=${item.tg_file_id}` : item.video_url)
        : (item.tg_file_id ? `tgfile://${item.tg_file_id}` : "");
      const ok = await dispatchGH(env, "publish_video.yml", {
        video_url: ytVideoUrl,
        title: item.title,
        description: item.description,
        tags: item.tags,
        mode: item.mode,
        category: item.category,
        privacy: ytPrivacy,
      });
      const privLbl = ytPrivacy === "public" ? "PUBLIC 🚀" : "Unlisted 🔒";
      report.push(ok
        ? `▶️ YouTube (${privLbl}): Upload shuru ho gaya (~1 min me link yahin aayega!)`
        : "❌ YouTube trigger fail: Check karo .github/workflows/publish_video.yml GitHub par updated hai ya nahi.");
    }

    if (doMeta) {
      const fbRes = await publishFacebookPage(env, item);
      report.push(fbRes.msg);
      if (item.mode !== "LONG") {
        const igRes = await publishInstagramReelAndStory(env, item);
        report.push(igRes.msg);
        if (igRes.pendingContainer) pendingIgCid = igRes.pendingContainer;
      } else {
        report.push("ℹ️ Long (16:9) video ke liye Instagram Reels auto-skip kiya gaya.");
      }
    }

    const retryRows = [];
    if (pendingIgCid) {
      retryRows.push([{ text: "🔄 Complete IG Reel Publish", callback_data: `pub:${id}:igfin:${pendingIgCid}` }]);
    }
    const anyFailed = report.some(line => line.includes("❌") || line.includes("⚠️"));
    if (anyFailed) {
      retryRows.push([
        { text: "🔄 Sab Retry (PUBLIC)", callback_data: `pub:${id}:all_pub` },
        { text: "▶️ YT PUBLIC Retry", callback_data: `pub:${id}:yt_pub` },
      ]);
      retryRows.push([
        { text: "📱 FB + IG Retry", callback_data: `pub:${id}:meta` },
        { text: "📋 Full Publish Menu", callback_data: `pub:${id}:card` },
      ]);
    }
    const replyMarkup = retryRows.length ? { inline_keyboard: retryRows } : undefined;
    if (msgId) {
      await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: report.join("\n\n").slice(0, 3950), reply_markup: replyMarkup });
    } else {
      await tgApi(env, "sendMessage", { chat_id: chatId, text: report.join("\n\n").slice(0, 3950), reply_markup: replyMarkup });
    }
  } catch (err) {
    const em = `❌ Auto-Publish error: ${String(err).slice(0, 220)}`;
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: em });
    else if (chatId) await tgReply(env.TG_TOKEN, chatId, em, false);
  }
}


// =========================================================================
// v4.02: INSTANT /log DOWNLOADABLE FILE SYSTEM + /vfilter REVERSIBLE TOGGLE
// =========================================================================
const LAST_LOG_PATH = "seekha/last_run_log.json";
const SETTINGS_PATH = "seekha/aapki_settings.json";

async function registerRunLog(env, payload) {
  const cur = await readGhJson(env, LAST_LOG_PATH, {});
  const entry = {
    ts: Date.now(),
    title: String(payload.title || "Latest Video").slice(0, 120),
    mode: String(payload.mode || "SHORT").toUpperCase(),
    status: String(payload.status || "done"),
    elapsed: String(payload.elapsed || ""),
    log_url: String(payload.log_url || ""),
    log_file_id: String(payload.log_file_id || ""),
    vrep_file_id: String(payload.vrep_file_id || ""),
    tail: String(payload.tail || "").slice(-1800),
  };
  await writeGhJson(env, LAST_LOG_PATH, entry, cur.sha, `save last run log (${entry.mode})`);
}

async function sendLatestLogFiles(env, chatId) {
  const cur = await readGhJson(env, LAST_LOG_PATH, null);
  const info = cur && cur.data && typeof cur.data === "object" ? cur.data : null;
  let sentDoc = false;

  if (info && (info.log_file_id || info.log_url || info.vrep_file_id)) {
    const cap = `📋 Last Video Log (${info.mode || "SHORT"} • ${info.status || "done"}${info.elapsed ? " • " + info.elapsed : ""})\n🎬 ${(info.title || "").slice(0, 90)}\n\n👉 Ye file seedha Gemini ko forward kar do!`;
    if (info.log_file_id) {
      const r = await tgApi(env, "sendDocument", { chat_id: chatId, document: info.log_file_id, caption: cap.slice(0, 950) });
      if (r && r.ok) sentDoc = true;
    }
    if (!sentDoc && info.log_url) {
      const r = await tgApi(env, "sendDocument", { chat_id: chatId, document: info.log_url, caption: cap.slice(0, 950) });
      if (r && r.ok) sentDoc = true;
    }
    if (info.vrep_file_id) {
      await tgApi(env, "sendDocument", {
        chat_id: chatId,
        document: info.vrep_file_id,
        caption: `🧾 Visual Report — ${(info.title || "").slice(0, 80)}`,
      });
    }
    if (!sentDoc && info.tail) {
      await tgReply(env.TG_TOKEN, chatId, `📋 Last Video Log Tail (${info.title || ""}):\n\n${info.tail.slice(-3200)}`, false);
      sentDoc = true;
    }
  }

  if (!sentDoc) {
    const summary = await getRunsSummary(env);
    await tgReply(
      env.TG_TOKEN,
      chatId,
      `ℹ️ Abhi koi naya v4.02 video log saved nahi hai (agli video bante hi /log par seedha downloadable .txt file aayegi).\n\n${summary}`,
      true
    );
  }
}

async function getVfilterEnabled(env) {
  const cur = await readGhJson(env, SETTINGS_PATH, []);
  const arr = Array.isArray(cur.data) ? cur.data : [];
  return { enabled: !arr.includes("vfilter_off"), arr, sha: cur.sha };
}

async function setVfilterState(env, chatId, enable) {
  const st = await getVfilterEnabled(env);
  const next = st.arr.filter(x => x !== "vfilter_off");
  if (!enable) next.push("vfilter_off");
  await writeGhJson(env, SETTINGS_PATH, next, st.sha, `vfilter ${enable ? "on" : "off"}`);
  const msg = enable
    ? "✅ Visual Quality Filter ON kar diya!\nBlurry / low-res / ganda visuals ab auto-reject honge.\n(Voice fix, Copyright Shield aur /log 100% active hain.)"
    : "↩️ Visual Quality Filter OFF kar diya (Purana v4.0 Visual Mode wapas)!\n✅ Aapka Voice fix, Copyright Screenshot Shield aur /log system 100% SAFE & ACTIVE hain.";
  await tgReply(env.TG_TOKEN, chatId, msg, true);
}

async function showVfilterMenu(env, chatId) {
  const st = await getVfilterEnabled(env);
  await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: `🎨 Visual Quality Filter abhi: ${st.enabled ? "✅ ON (Blurry/Low-res reject)" : "↩️ OFF (Purana Visual Mode)"}\n\nNote: Isko OFF karne par sirf visual filter purana hota hai — Voice fix, Copyright Shield aur /log bilkul nahi hatenge!`,
    reply_markup: {
      inline_keyboard: [[
        { text: "✅ Filter ON", callback_data: "vf:on" },
        { text: "↩️ Filter OFF (Purana Mode)", callback_data: "vf:off" },
      ]],
    },
  });
}

async function handleVfilterCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const enable = cq.data === "vf:on";
  await setVfilterState(env, chatId, enable);
}


// =========================================================================
// v4.05: 1-TAP RE-UPLOAD / RE-PUBLISH VAULT (/republish, /publish, Video Forward)
// =========================================================================
function buildPublishKeyboard(id, isLong) {
  return isLong ? {
    inline_keyboard: [
      [{ text: "🚀 YT PUBLIC + FB Page", callback_data: `pub:${id}:all_pub` }],
      [{ text: "✅ YT Unlisted + FB Page", callback_data: `pub:${id}:all` }],
      [{ text: "▶️ YT PUBLIC", callback_data: `pub:${id}:yt_pub` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf Facebook Page", callback_data: `pub:${id}:meta` }, { text: "❌ Skip", callback_data: `pub:${id}:skip` }],
    ],
  } : {
    inline_keyboard: [
      [{ text: "🚀 Sab Par PUBLIC (YT + FB + IG + Story)", callback_data: `pub:${id}:all_pub` }],
      [{ text: "✅ Sab Par (YT Unlisted + FB + IG + Story)", callback_data: `pub:${id}:all` }],
      [{ text: "▶️ YT PUBLIC", callback_data: `pub:${id}:yt_pub` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf FB + IG + Story", callback_data: `pub:${id}:meta` }, { text: "❌ Skip", callback_data: `pub:${id}:skip` }],
    ],
  };
}

async function sendPublishCardForItem(env, chatId, item) {
  const isLong = String(item.mode || "SHORT").toUpperCase() === "LONG";
  const hasAssets = (item.cover_tg_file_id || item.cover_url ? "🖼️ Cover ✓ " : "") +
    (item.story_tg_file_id || item.story_url ? "✨ Story ✓" : "");
  const cardText =
    `🚀 Auto-Publish Ready! (${isLong ? "LONG 16:9" : "SHORT 9:16"})\n\n` +
    `🎬 Title: ${String(item.title || "The Viral Gyaan").slice(0, 95)}\n` +
    (hasAssets ? `🎨 Assets: ${hasAssets.trim()}\n` : "") +
    `📝 Desc: ${String(item.description || "").slice(0, 240)}\n\n` +
    `👇 Kahan aur kaise publish karun?`;
  await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: cardText.slice(0, 3900),
    reply_markup: buildPublishKeyboard(item.id, isLong),
  });
}

async function showRepublishVault(env, chatId) {
  const cur = await readGhJson(env, PUB_PATH, {});
  const store = (cur.data && typeof cur.data === "object") ? cur.data : {};
  const list = Object.values(store).sort((a, b) => (b.ts || 0) - (a.ts || 0)).slice(0, 10);
  if (!list.length) {
    await tgReply(env.TG_TOKEN, chatId, "ℹ️ Abhi vault me koi saved video nahi hai. Nayi video banne ke baad ya koi purani video forward karke publish kar sakte ho!", true);
    return;
  }
  const kb = {
    inline_keyboard: list.map((it, idx) => [{
      text: `${idx + 1}. [${it.mode === "LONG" ? "LONG" : "SHORT"}] ${String(it.title || "Video").slice(0, 42)}`,
      callback_data: `pub:${it.id}:card`,
    }]),
  };
  await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: `📂 Saved Videos Vault (Aakhri ${list.length} videos — Cover, Story aur Caption ke saath!)\n\n👇 Jis video ko dobara YouTube / FB / IG par upload karna hai uspe tap karo:`,
    reply_markup: kb,
  });
}

async function handleManualPublishUrl(env, chatId, rawArgs) {
  const parts = rawArgs.split("|").map(s => s.trim()).filter(Boolean);
  let mode = "SHORT";
  if (parts[0] && /^(LONG|SHORT)$/i.test(parts[0])) {
    mode = parts.shift().toUpperCase();
  }
  const url = parts[0] || "";
  const title = parts[1] || "The Viral Gyaan";
  if (!/^https?:\/\/\S+/i.test(url)) {
    await tgReply(
      env.TG_TOKEN,
      chatId,
      "⚠️ Sahi format:\n/publish https://files.catbox.moe/xxxxx.mp4 | Aapka Video Title\n\n(Long 16:9 video ke liye: /publish LONG | https://... | Title)",
      false
    );
    return;
  }
  await registerPublishCard(env, {
    chat_id: chatId,
    mode,
    category: "general",
    video_url: url,
    title,
    description: `${title}\n\n#TheViralGyaan ${mode === "SHORT" ? "#shorts #facts #viral" : "#hindifacts"}`,
    ig_caption: `${title}\n\n#TheViralGyaan #reels #facts`,
    tags: "TheViralGyaan, facts, hindi, viral",
  });
}

async function handleForwardedVideoPublish(env, chatId, videoObj, caption) {
  const sizeMb = (Number(videoObj.file_size || 0) / (1024 * 1024));
  const title = (caption || "").split("\n")[0].replace(/^✅\s*\[(SHORT|LONG)\]\s*/i, "").trim().slice(0, 95) || "The Viral Gyaan";
  const isLong = Number(videoObj.width || 0) > Number(videoObj.height || 0);
  const mode = isLong ? "LONG" : "SHORT";

  if (sizeMb > 19.8) {
    await tgReply(
      env.TG_TOKEN,
      chatId,
      `⚠️ Ye purani video ${sizeMb.toFixed(1)} MB ki hai (Telegram Bot 20 MB se badi forwarded file download nahi kar sakta).\n\n✅ 10-Second Tarika:\n1) Phone browser me catbox.moe khol kar ye video upload karo\n2) Mila hua link yahan bhejo:\n/publish <link> | ${title}\n\n(Note: Ab se banne wali har nayi video me /republish par 1-tap direct retry chalega — chahe 100 MB ki ho!)`,
      false
    );
    return;
  }

  await registerPublishCard(env, {
    chat_id: chatId,
    mode,
    category: "general",
    tg_file_id: videoObj.file_id,
    video_url: "",
    title,
    description: `${title}\n\n#TheViralGyaan ${mode === "SHORT" ? "#shorts #facts #viral" : "#hindifacts"}`,
    ig_caption: `${title}\n\n#TheViralGyaan #reels #facts`,
    tags: "TheViralGyaan, facts, hindi, viral",
  });
}
