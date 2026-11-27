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
    [{ text: "🔥 /trends" }, { text: "📈 /planner" }],
    [{ text: "📂 /republish" }, { text: "📜 /log" }, { text: "📊 /status" }],
    [{ text: "🎬 /vmode" }, { text: "🎨 /vfilter" }, { text: "🛑 /rok" }],
    [{ text: "📅 /schedule" }, { text: "📖 /guide" }],
    [{ text: "▶️ Aaj shuru karo (5 Prompt)" }, { text: "🎬 Long Prompt" }],
  ],
  resize_keyboard: true,
  is_persistent: true,
};

const BOT_COMMANDS = [
  { command: "trends", description: "🔥 SHORT & LONG viral topics (YouTube + X/IG/FB News + Influencer)" },
  { command: "planner", description: "📈 Auto-Pilot Winner Category & Views Tracker" },
  { command: "republish", description: "📂 Last 10 videos (Cover+Story) 1-tap Re-Upload" },
  { command: "schedule", description: "📅 Smart 3/Day Auto-Publish Schedule Queue (IST)" },
  { command: "publish", description: "📤 Purani 20-200MB video catbox link se publish" },
  { command: "log", description: "📜 Last video ki downloadable log + Visual Report" },
  { command: "vmode", description: "🎬 Visual Mode: AI Cinematic vs Stock Search" },
  { command: "vfilter", description: "🎨 Visual Quality Filter ON / OFF" },
  { command: "status", description: "📊 Live cloud render progress" },
  { command: "rok", description: "🛑 Chal rahi video turant rokein" },
  { command: "competitors", description: "👥 Tracked competitor channels badlein" },
  { command: "purana", description: "⏪ Pichhle version par rollback" },
  { command: "start", description: "🔄 Menu & Commands refresh karein" },
];

const SHORTS_PROMPT = `MERA TOPIC (1 se 5 topic likho, ya "AUTO" rehne do to 5 alag-alag viral trending topics khud chuno):
<<< AUTO >>>

You are India's #1 viral Hindi YouTube Shorts Director & Scriptwriter for "The Viral Gyaan" (science, army/defence, news, business, history, tech, crime/mystery, sports, influencers).
My automated VideoTool reads EVERY line, applies the EXACT category editing style you choose via MODE:, triggers real pro editing effects from your [tags], renders 30fps AI explainers & realistic AI scenes, and picks visuals STRICTLY from your "||" hints (verified by AI Vision Judge + CLIP!).
Write 5 complete, high-retention Hindi Shorts scripts separated by a line with only ==== (each video MUST feel unique and matched to its category!).

1) CHOOSE CATEGORY EDITING MODE (line 1 of EACH script — controls colour grade, cut speed, film/particle layer, and SFX):
   MODE: science | army | news | business | history | mystery | sports | influencer | technology | general

2) STRICT MICRO-BEAT SCRIPT RULES (40-55 sec, 14-18 SHORT lines, 5-9 words per line — ONE single visual idea/emotion per line):
   - NEVER mix 2 contrasting ideas in 1 line! Split into 2 short lines so each emotion/subject gets its OWN exact visual.
   - HOOK (Line 1): Shocking/curious hook in first 2s. NEVER start with "दोस्तों" or "क्या आप जानते हैं".
   - Write ALL numbers & years in ENGLISH digits (e.g., 1999, 2026, 15 Lakh — NEVER Hindi digits like १९९९, NEVER ** bold markdown, NEVER Chinese/Bengali characters!).
   - Last line CTA MUST ALSO end with "|| <hero closing visual of main topic>" (NEVER "tv screen" or "phone in hand"!): ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना। || <hero closing visual of main topic>

3) PRO EDITING TAGS (put at END of Hindi line, right BEFORE "||" — use tastefully per category, max 4-5 tags per script):
   - [explain: <short mechanism/diagram/process to animate in 30fps>] -> dynamic 30fps HTML5/Canvas explainer (1-2 per Short on lines explaining HOW something works, comparisons, science/tech/finance/anatomy — NEVER on real living celebrities!)
   - [route: PlaceA -> PlaceB | Stat] -> dark night-lights satellite route/flight/money-flow map!
   - [map: Place, Country] -> animated 3D satellite map zoom (MAX 1 per Short — NEVER repeat the same country!)
   - [news: Short Headline | Source] -> realistic newspaper proof card with yellow highlighter sweep (great for news/business/crime/history)
   - [label: 2026 / 828m / ₹500 Cr] -> crisp red typewriter date/number badge (great for science/business/sports)
   - [ink] -> dramatic red ink-splash transition on the biggest twist line!
   - SFX tags (max 2-3 per script — NEVER write [riser], opening riser is automatic!): [impact] on shock/army/reveal, [whoosh] on fast jump, [ding] on stat/fact, [typing] on tech/news.

4) VISUAL HINT RULES (MOST IMPORTANT — EVERY SINGLE LINE INCLUDING LAST CTA MUST HAVE "||"):
   - STRICT COUNTRY & PERSON ANCHOR: Every "||" hint MUST include the EXACT country/city/person/entity of that line (3-5 simple lowercase English camera words, e.g., "pakistan karachi street protest", "isro rocket launch sriharikota", "ratan tata nano 2008", "grey wolf pack snow"). NEVER use bare generic hints like "protest flag", "flag waving", "military statue", "tv screen", "phone in hand", "rock concert", "new year balloons", "shocked face", "question mark", "subscribe animation".
   - SMART AUTO AI REALISTIC SCENES (1-4 lines where real stock footage fails or does not exist — e.g., wildlife emotion/action like "grey wolf lovingly nuzzling wolf cubs snow forest" or "wolf leaping across snowy mountain cliff", feats of strength like "giant muscular strongman lifting heavy man arena dramatic lighting", ancient history, space/deep-sea):
     * Format: || AI: <8-14 vivid photorealistic documentary words>
     * NEVER use "|| AI:" for real living politicians/celebrities/news people!
   - STRICTLY BANNED in "||" hints: "reconstruction", "reenactment", "examination", "prehistoric", "cinematic", "footage", "growth", "economy", "crisis", "secret", "interview", "podcast", "chart", "slide", "tv screen", "phone in hand", "[YT]", "[X]", emojis, hashtags, bold (**), or numbering.

OUTPUT EXACTLY THIS (copy-paste ready for Telegram Bot):
MODE: <category>
TITLE: <2-4 crisp words> | <2-4 hook words ONLY — NEVER add a 3rd pipe '|'>
<hook line> [impact] || <exact country/entity-anchored visual hint>
<line 2> [map: Place, Country] || <exact concrete visual hint>
<explainer line> [explain: <mechanism/diagram to animate in 30fps>] || <fallback concrete visual hint>
<wildlife/action line> || AI: <8-14 vivid photorealistic documentary words>
<twist line> [ink] [impact] || <exact concrete visual hint>
...
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना। || <hero closing visual of main topic>
====
MODE: <different category for Script 2>
TITLE: <Script 2> | <hook>
...`;

const LONG_PROMPT = `MERA TOPIC (Long News + Fact Documentary Video):
<<< yahan apna topic ya breaking news + fact likho >>>

You are India's #1 Hindi Long-Form Documentary Director & Scriptwriter (Dhruv Rathee / Nitish Rajput / MagnatesMedia style) for "The Viral Gyaan".
My automated VideoTool renders 16:9 documentary videos with calm 5-second pacing, category-matched colour grading, dynamic 30fps AI explainers, glowing satellite route maps, realistic broadsheet news proof cards, and pinpoint country/person-anchored visuals from your "||" hints.

STRUCTURE (STRICTLY 5-6 min, 42-55 lines, ~750-880 Hindi words, 10-16 words per line):
- Line 1: LONG
- Line 2: MODE: news | army | science | business | history | mystery | sports | influencer | technology
- Line 3: TITLE: <45-60 char high-CTR Hindi title> | <2-3 bold Hindi thumbnail words ONLY — NEVER add a 3rd pipe '|'>
- Cold Open Hook (0-25s) with high stakes -> Escalation with real numbers/dates/proof -> Big Reveal -> Short comment-question CTA.
- Write ALL numbers & years in ENGLISH digits (e.g., 1999, 2026, 10 Billion — NEVER Hindi digits like १९९९, NEVER ** bold markdown, NEVER Chinese/Bengali characters!).
- Only add "## Chapter Title" headings if you want clean named chapters (NEVER write "भाग 2" or generic numbers).

PRO EDITING TAGS (put at END of Hindi line, right BEFORE "||"):
- [explain: <clear mechanism/comparison/process to animate in 30fps>] -> dynamic 30fps HTML5/Canvas explainer (2-4 per Long script on lines explaining HOW something works, science/tech/finance/law/geopolitics/anatomy breakdowns — NEVER on real living celebrities!)
- [route: PlaceA -> PlaceB | Stat] -> dark night-lights satellite route/flight/money-flow map (1-2 lines where movement/connection matters)
- [map: Place, Country] -> MAX 2 times in the ENTIRE Long script (NEVER repeat the same country!)
- [news: Short Headline | Official Source] -> realistic newspaper proof card with yellow highlighter sweep (2-3 proof/report/court/date lines)
- [label: Year / Stat] -> 2-3 key timeline or number badges
- [ink] or [impact] on major reveals (NEVER write [riser], opening riser is automatic!).

VISUAL HINT RULES (EVERY SINGLE LINE INCLUDING LAST CTA MUST HAVE "||"):
- STRICT COUNTRY & PERSON ANCHOR: Every "||" hint MUST include the EXACT country/city/person/entity of that line (3-5 simple lowercase English camera words, e.g., "pakistan karachi street protest crowd", "asim munir pakistan army general", "india parliament delhi exterior"). NEVER bare generic words like "protest flag", "flag waving", "military statue", "tv screen", "phone in hand", "rock concert", "new year 2025", "question mark", "subscribe animation", "economy", "growth", "crisis", "secret", "interview", "chart", "slide".
- SMART AUTO AI REALISTIC SCENES (up to 25% of lines where real stock footage fails or does not exist — e.g., wildlife emotion/action like "grey wolf lovingly nuzzling wolf cubs snow forest" or "wolf leaping across snowy mountain cliff", feats of strength like "muscular strongman lifting heavy boulder arena dramatic lighting", ancient history, space/deep-sea):
  * Format: || AI: <8-14 vivid photorealistic documentary words>
  * NEVER use "|| AI:" for real living politicians/celebrities/news people!
- Last CTA line MUST end with "|| <cinematic hero closing visual of main topic>" (NEVER "tv screen" or "phone in hand"!).
- NO emojis, NO hashtags, NO bold (**), NO numbering, NO extra notes.

OUTPUT EXACTLY:
LONG
MODE: <category>
TITLE: <documentary title> | <2-3 bold thumbnail words>
<hook line> [impact] || <exact country/entity-anchored visual hint>
<geography line> [map: Place, Country] || <exact concrete visual hint>
<explainer line> [explain: <mechanism/diagram to animate in 30fps>] || <fallback concrete visual hint>
<proof line> [news: Short Headline | Official Source] || <exact concrete visual hint>
<wildlife/action line> || AI: <8-14 vivid photorealistic documentary words>
...
इस पूरे मामले पर आपकी क्या राय है? कमेंट में ज़रूर बताएं और ऐसे ही रिसर्च वीडियो के लिए सब्सक्राइब करें। || <cinematic hero closing visual of main topic>`;

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
• 🎬 /vmode: AI Cinematic Mode (100% script-matched realistic visuals) vs Purana Stock Search.
• 🎨 /vfilter: Visual Quality Filter ON/OFF.
• 📦 Update: Koi bhi nayi .zip file caption "update" ke saath bhejo -> cloud 30 sec me update!
• ⏪ /purana: Pichhle version par wapas jaane ke liye.`;

export default {
  async fetch(request, env, ctx) {
    // v4.31: FREE Cloudflare Workers AI FLUX.1-schnell proxy route for GitHub Actions (authenticated by TG_TOKEN)
    if (request.method === "POST" && new URL(request.url).pathname === "/ai-image") {
      const auth = (request.headers.get("X-VG-Auth") || "").trim();
      if (!env.TG_TOKEN || auth !== String(env.TG_TOKEN).trim()) {
        return new Response("unauthorized", { status: 401 });
      }
      if (!env.AI) {
        return new Response(JSON.stringify({ error: "Workers AI binding (AI) not attached" }), {
          status: 503, headers: { "Content-Type": "application/json" },
        });
      }
      try {
        const body = await request.json();
        const out = await env.AI.run("@cf/black-forest-labs/flux-1-schnell", {
          prompt: String(body.prompt || "").slice(0, 1200),
          steps: Math.min(8, Math.max(4, Number(body.steps || 6))),
        });
        return new Response(JSON.stringify({ image: out && out.image ? out.image : "" }), {
          status: 200, headers: { "Content-Type": "application/json" },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e).slice(0, 160) }), {
          status: 500, headers: { "Content-Type": "application/json" },
        });
      }
    }
    if (request.method === "GET" || request.method === "HEAD") {
      const u = new URL(request.url);
      if (u.pathname.startsWith("/media/tg/")) {
        return handleTgMediaBridge(env, u.pathname, u.searchParams.get("fb") || "", request.method === "HEAD");
      }
      if (u.pathname === "/media/proxy") {
        return handleProxyMediaBridge(u.searchParams.get("u") || "", u.searchParams.get("t") || "mp4", request.method === "HEAD");
      }
      return new Response("VideoTool Cloud Bridge v4.28 Auto-Pilot is LIVE!", { status: 200 });
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
      } else if (cdata.startsWith("scancel:")) {
   await handleScheduleCancel(env, update.callback_query);
   return new Response("ok");
 }
 if (cdata.startsWith("vm:")) {
        await handleVmodeCallback(env, update.callback_query);
      } else if (cdata.startsWith("pl:")) {
        const p = handlePlannerCallback(env, update.callback_query);
        if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
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

    // 2) Start / Menu / Guide (+ auto-sync Telegram "/" command autocomplete menu!)
    if (tl === "/start" || tl === "/menu") {
      await tgApi(env, "setMyCommands", { commands: BOT_COMMANDS });
      await tgReply(env.TG_TOKEN, chatId,
        "☁️ VideoTool Cloud v4.17 Auto-Pilot LIVE hai!\n✅ Short/Long alag Trends, Influencer category, Full-Screen Shorts aur Realistic Newspaper sab active hain:", true);
      return new Response("ok", { status: 200 });
    }
    if (tl === "/guide" || text.includes("/guide")) {
      await tgReply(env.TG_TOKEN, chatId, GUIDE_TEXT, true);
      return new Response("ok", { status: 200 });
    }

    // 2b) v4.10: 🔥 /trends (Separate SHORT 9:16 vs LONG 5-6m 16:9 + Category Viral Scripts)
    if (tl === "/trends" || tl === "/trend" || tl === "trends" || tl === "trend" || text.includes("/trends")) {
      const p = handleTrendsCommand(env, chatId);
      if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
      return new Response("ok", { status: 200 });
    }
    // 2c) v4.10: 📈 /planner (Winner-Lock & Auto-Pivot Stats Brain + Manual Daily/Long Trigger)
    if (tl === "/planner" || tl.startsWith("/planner ") || text.includes("/planner")) {
      const p = handlePlannerCommand(env, chatId, text);
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

    // 5b.4) v4.34 Smart 3/Day Publish Schedule Queue (/schedule)
    if (tl === "/schedule" || tl.startsWith("/schedule ") || text.includes("/schedule")) {
      await showScheduleQueue(env, chatId);
      return new Response("ok");
    }
    // 5b.5) v4.27 Visual Mode Switch (/vmode ai | /vmode stock | /vmode)
    if (tl === "/vmode" || tl.startsWith("/vmode ") || text.includes("/vmode")) {
      const arg = tl.replace(/.*\/vmode/, "").trim();
      if (arg === "ai" || arg === "cinematic" || arg === "on") {
        await setVmodeState(env, chatId, true);
      } else if (arg === "stock" || arg === "purana" || arg === "off") {
        await setVmodeState(env, chatId, false);
      } else {
        await showVmodeMenu(env, chatId);
      }
      return new Response("ok", { status: 200 });
    }
    // 5c) v4.02 Reversible Visual Quality Filter Toggle (/vfilter on | /vfilter off | /vfilter)
    if (tl === "/vfilter" || tl.startsWith("/vfilter ") || text.includes("/vfilter")) {
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
    if (tl === "/republish" || tl === "/reupload" || tl.startsWith("/republish ") || text.includes("/republish")) {
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

  // v4.10 AUTO-PILOT CRON:
  //   30 3 * * *       -> Daily 9:00 AM IST  (5 Viral Shorts topics — 70-80% Winner Category!)
  //   30 11 * * 0,2,4  -> Tue/Thu/Sun 5:00 PM IST (5 Viral Long 5-6 min 16:9 topics!)
  async scheduled(event, env, ctx) {
    const p = Promise.allSettled([runAutoPilotCron(env, event && event.cron ? event.cron : ""), runScheduledPublishes(env)]);
    if (ctx && ctx.waitUntil) ctx.waitUntil(p); else await p;
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
  const rawParts = splitScripts(orig);
  let upgradedAny = false;
  const items = [];
  for (const sc of rawParts) {
    // v4.22 Auto Hint Doctor: auto-upgrade weak/missing/trap '||' hints on pasted scripts too (fast 8.5s cap, silent fallback)
    const opt = (rawParts.length === 1) ? await autoOptimizePastedScript(env, sc, mode === "L") : { script: sc, upgraded: false };
    if (opt.upgraded) upgradedAny = true;
    items.push({ script: opt.script, mode: vmode, ts: Date.now() });
  }
  const optNote = upgradedAny ? "\n🧠 Auto Hint Doctor: weak visual hints apne-aap upgrade kar diye ✓" : "";
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
  const ok = await dispatchGH(env, "make_video.yml", { script: next.script, mode: next.mode || "SHORT" });
  if (ok) {
    await saveQueue(env, rest, q.sha);
  }
  if (chatId) {
    const firstLn = (next.script || "").split("\n").find(l => l.trim() && !/^(MODE|TITLE|LONG)/i.test(l.trim())) || "Agli video";
    await tgReply(env.TG_TOKEN, chatId, ok
      ? `▶️ Queue se agli ${next.mode || "SHORT"} video shuru ho gayi! (Baaki ${rest.length} line me)\n${firstLn.slice(0, 60)}`
      : `⚠️ Queue se agli video start nahi ho paayi (${LAST_GH_DISPATCH_ERR || "dispatch fail"}) — video queue me safe hai!`, true);
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

let LAST_GH_DISPATCH_ERR = "";
async function dispatchGH(env, workflowFile, inputs) {
  LAST_GH_DISPATCH_ERR = "";
  const cleanInputs = {};
  for (const [k, v] of Object.entries(inputs || {})) {
    cleanInputs[k] = (v === undefined || v === null) ? "" : String(v);
  }
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await ghFetch(env, `/actions/workflows/${workflowFile}/dispatches`, "POST", { ref: "main", inputs: cleanInputs });
      if (res.ok || res.status === 204) return true;
      const body = (await res.text().catch(() => "")).slice(0, 140).replace(/\s+/g, " ");
      LAST_GH_DISPATCH_ERR = `HTTP ${res.status}${body ? ": " + body : ""}`;
      if (res.status < 500 && res.status !== 429) return false;
    } catch (e) {
      LAST_GH_DISPATCH_ERR = String(e).slice(0, 120);
    }
    await sleepMs(800);
  }
  return false;
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
  "@GetsetflyFACT",
  "@AbhiandNiyu",
  "@A2Motivation",
  "@ItsFacts",
  "@RighttoShiksha",
  "@Fact2Fact",
  "@GauravThakur-GSF",
  "@ThinkSchool",
  "@dhruvrathee",
  "@NitishRajput",
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
    visualRule: "Use exact real-world objects, places, NASA/wildlife/science HD scenes — NEVER abstract words like shocked face or question mark.",
    shortHandles: null, // uses saved /competitors list (DEFAULT_COMPETITORS)
    longHandles: ["@FactTechz", "@GauravThakur-GSF", "@GetsetflySCIENCE", "@AntarikshTV", "@zemtv", "@VigyanTvIndia", "@dhruvrathee", "@NitishRajput", "@ThinkSchool", "@MohakMangal"],
  },
  business: {
    label: "💼 Business & History",
    modeHint: "business | history | mystery",
    visualRule: "CRITICAL FOR BUSINESS/HISTORY (Nitish Rajput / Dhruv Rathee style): Name the exact company, founder, monument, map, or news event (e.g., 'tata motors factory line', 'indian parliament building delhi').",
    shortHandles: ["@ThinkSchool", "@A2Motivation", "@NitishRajput", "@dhruvrathee", "@LabourLawAdvisor", "@warikoo"],
    longHandles: ["@NitishRajput", "@dhruvrathee", "@ThinkSchool", "@GauravThakur-GSF", "@MohakMangal", "@StudyIQEducationLtd"],
  },
  influencer: {
    label: "🔥 Influencer & Creator News",
    modeHint: "influencer | news",
    visualRule: "CRITICAL FOR INFLUENCER NEWS: Name the exact creator, event, stage, podcast studio, or platform screen in every '||' hint (e.g., 'bhuvan bam stage event', 'carryminati gaming setup', 'youtube studio analytics mobile') — NEVER generic 'shocked face' or 'subscribe screen'.",
    shortHandles: ["@NeonMan", "@NeuzBoy", "@TriggeredInsaan", "@FukraInsaan", "@TechBurnerShorts", "@ManojDey"],
    longHandles: ["@NeonMan", "@NeuzBoy", "@MohakMangal", "@NitishRajput", "@dhruvrathee", "@DecodingYT"],
  },
  tech: {
    label: "📱 Tech & AI Updates",
    modeHint: "technology | news",
    visualRule: "CRITICAL FOR TECH/AI/UPDATES: Every '||' visual hint MUST include the EXACT smartphone, app, or AI tool name (e.g., 'iphone 17 pro camera closeup', 'instagram reels screen', 'chatgpt app interface') — NEVER generic 'technology' or 'view counter'.",
    shortHandles: ["@TechBurner", "@TrakinTech", "@TechBar", "@ManojDey", "@CreatorSearch2", "@TechnicalYogi"],
    longHandles: ["@TechBurner", "@TechnicalGuruji", "@GyanTherapy", "@Beebom", "@DecodingYT", "@aiuncovered"],
  },
  movies: {
    label: "🎬 Movies & Reviews",
    modeHint: "influencer",
    visualRule: "CRITICAL FOR MOVIES: Every '||' visual hint MUST include the EXACT movie/web-series title or lead actor/scene name (e.g., 'pushpa 2 trailer action', 'kalki movie scene closeup') and keep narration 100% original review/breakdown style (copyright-safe).",
    shortHandles: ["@PJExplained", "@FilmiIndian", "@YogiBoltaHai", "@ComicVerse", "@BnfTV", "@MenOfCulture"],
    longHandles: ["@PJExplained", "@FilmiIndian", "@YogiBoltaHai", "@ComicVerse", "@BnfTV", "@TriedRefusedProductions"],
  },
  updates: {
    label: "📱 Tech & AI Updates",
    modeHint: "technology | news",
    visualRule: "CRITICAL FOR APP/PLATFORM UPDATES: Every '||' visual hint MUST name the EXACT platform/app screen or AI tool.",
    shortHandles: ["@ManojDey", "@CreatorSearch2", "@TechnicalYogi", "@DecodingYT", "@TechBurnerShorts", "@aiuncovered"],
    longHandles: ["@DecodingYT", "@ManojDey", "@TechnicalYogi", "@TechBurner", "@GyanTherapy", "@aiuncovered"],
  },
  socialnews: {
    label: "🌐 X / IG / FB Viral News",
    modeHint: "news | influencer | business | technology",
    visualRule: "CRITICAL FOR VIRAL SOCIAL NEWS: Use concrete real-world people, locations, official press/event scenes, and [news:] / [route:] cards — NEVER generic vlogs.",
    shortHandles: ["@NeonMan", "@NeuzBoy", "@AbhiandNiyu", "@A2Motivation", "@ThinkSchool", "@TheLallantop", "@TechBurnerShorts", "@NitishRajput"],
    longHandles: ["@NitishRajput", "@dhruvrathee", "@AbhiandNiyu", "@MohakMangal", "@TheLallantop", "@StudyIQEducationLtd", "@ThinkSchool", "@NeonMan"],
    isSocialRss: true,
  },
  mix: {
    label: "🌍 Mix All (Top Viral)",
    modeHint: "science | business | history | influencer | technology | mystery",
    visualRule: "Include the exact concrete person/object/place/app name in every '||' visual hint so sharp HD visuals load.",
    shortHandles: ["@FactsMine", "@FactTechz", "@GetsetflyFACT", "@AbhiandNiyu", "@A2Motivation", "@RighttoShiksha", "@Fact2Fact", "@TechBurner", "@PJExplained", "@NeonMan", "@ThinkSchool", "@ManojDey"],
    longHandles: ["@NitishRajput", "@dhruvrathee", "@ThinkSchool", "@GauravThakur-GSF", "@FactTechz", "@MohakMangal", "@AbhiandNiyu", "@PJExplained", "@GetsetflySCIENCE", "@StudyIQEducationLtd"],
  },
};

const BORING_VLOG_RE = /\b(daily\s*vlog|my\s*vlog|mini\s*vlog|unboxing|bought\s*(a\s*)?new\s*(car|bike|phone|house|iphone)|room\s*tour|house\s*tour|home\s*tour|morning\s*routine|night\s*routine|grwm|get\s*ready\s*with\s*me|shopping\s*haul|24\s*hours?\s*challenge|prank\s*on|q\s*&\s*a|meet\s*my\s*(gf|bf|family|wife|husband)|my\s*new\s*car|car\s*delivery|first\s*day\s*vlog)\b/i;

function isBoringVlogTitle(title) {
  return BORING_VLOG_RE.test(String(title || ""));
}

function parseGoogleNewsRss(xmlText, catKey, fmt, defaultSource = "Trending India") {
  const items = [];
  const itemRe = /<item>([\s\S]*?)<\/item>/gi;
  let m;
  while ((m = itemRe.exec(String(xmlText || ""))) !== null) {
    const blk = m[1];
    const getTag = (tag) => {
      const r = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i").exec(blk);
      return r
        ? r[1]
            .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
            .replace(/<[^>]+>/g, "")
            .replace(/&amp;/g, "&")
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&apos;/g, "'")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/\s+/g, " ")
            .trim()
        : "";
    };
    const title = getTag("title");
    const link = getTag("link");
    const pubDate = getTag("pubDate");
    const source = getTag("source") || defaultSource;
    if (!title || title.length < 18 || isBoringVlogTitle(title)) continue;
    const pubMs = Date.parse(pubDate || "") || Date.now();
    const ageDays = Math.max(0, Math.round((Date.now() - pubMs) / 86400000));
    // Strict 15-day fresh window for social news
    if (ageDays > 15) continue;
    let h = 0;
    for (let i = 0; i < title.length; i++) h = ((h << 5) - h + title.charCodeAt(i)) | 0;
    const id = "gn_" + Math.abs(h).toString(36);
    items.push({
      id,
      title,
      channel: source,
      handle: "@ViralNews",
      catKey,
      fmt,
      views: 300000,
      dur: fmt === "LONG" ? 360 : 50,
      ageDays,
      outlierMult: 4.0,
      viralRating: 9.0,
      score: 1000 / Math.max(1, ageDays + 1),
      url: link || "https://news.google.com/?hl=en-IN&gl=IN&ceid=IN:en",
    });
  }
  return items;
}

async function scanSocialNewsTrends(env, excludeIds = [], fmt = "SHORT") {
  const isLongFmt = String(fmt || "SHORT").toUpperCase() === "LONG";
  const fmtStr = isLongFmt ? "LONG" : "SHORT";
  const seenSet = new Set((excludeIds || []).map(String));
  const feeds = isLongFmt
    ? [
        { url: "https://news.google.com/rss/search?q=India+viral+OR+controversy+OR+influencer+OR+business+when:14d&hl=en-IN&gl=IN&ceid=IN:en", src: "Google News India" },
        { url: "https://news.google.com/rss/search?q=YouTuber+OR+Instagram+OR+Twitter+trending+India+when:14d&hl=en-IN&gl=IN&ceid=IN:en", src: "Google News Social" },
        { url: "https://feeds.feedburner.com/ndtvnews-trending-news", src: "NDTV Trending" },
        { url: "https://timesofindia.indiatimes.com/rssfeedmostread.cms", src: "Times of India Trending" },
        { url: "https://www.hindustantimes.com/feeds/rss/trending/rssfeed.xml", src: "Hindustan Times Trending" },
      ]
    : [
        { url: "https://news.google.com/rss/search?q=viral+Instagram+OR+Twitter+OR+X+India+when:7d&hl=en-IN&gl=IN&ceid=IN:en", src: "Google News Social" },
        { url: "https://news.google.com/rss/search?q=Indian+YouTuber+OR+influencer+viral+news+when:10d&hl=en-IN&gl=IN&ceid=IN:en", src: "Google News Creator" },
        { url: "https://feeds.feedburner.com/ndtvnews-trending-news", src: "NDTV Trending" },
        { url: "https://timesofindia.indiatimes.com/rssfeedmostread.cms", src: "Times of India Trending" },
        { url: "https://www.hindustantimes.com/feeds/rss/trending/rssfeed.xml", src: "Hindustan Times Trending" },
      ];
  const reqHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
  };
  const fetched = await Promise.all(
    feeds.map(async (f) => {
      try {
        const r = await fetchWithTimeout(f.url, { headers: reqHeaders }, 7500);
        if (!r.ok) return [];
        const xml = await r.text();
        return parseGoogleNewsRss(xml, "socialnews", fmtStr, f.src);
      } catch (e) {
        return [];
      }
    })
  );
  const all = fetched.flat();
  const uniq = [];
  const seenTitle = new Set();
  for (const it of all) {
    const key = it.title.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 36);
    if (key && !seenTitle.has(key)) {
      seenTitle.add(key);
      uniq.push(it);
    }
  }
  uniq.sort((a, b) => a.ageDays - b.ageDays);
  const fresh = uniq.filter((x) => !seenSet.has(x.id));
  if (fresh.length >= 3) {
    return { items: fresh.slice(0, 5), recycled: false };
  }
  if (uniq.length >= 3) {
    return { items: uniq.slice(0, 5), recycled: true };
  }
  // Automatic YouTube Viral/Creator News backup if RSS feeds are blocked or empty
  const ytBackup = await scanCompetitorTrends(env, "socialnews", excludeIds, fmtStr);
  if (ytBackup && Array.isArray(ytBackup.items) && ytBackup.items.length) {
    return ytBackup;
  }
  return { items: uniq.slice(0, 5), recycled: false };
}

async function scanCompetitorTrends(env, catKey = "facts", excludeIds = [], fmt = "SHORT") {
  const ytKey = (env.YOUTUBE_KEY || "").trim();
  if (!ytKey) return { items: [], recycled: false };
  const isLongFmt = String(fmt || "SHORT").toUpperCase() === "LONG";
  const cat = TREND_CATEGORIES[catKey] || TREND_CATEGORIES.facts;
  let handles = isLongFmt ? cat.longHandles : cat.shortHandles;
  if (!handles || !handles.length) {
    const cur = await readGhJson(env, COMP_PATH, DEFAULT_COMPETITORS);
    const saved = Array.isArray(cur.data) && cur.data.length ? cur.data : DEFAULT_COMPETITORS;
    // Merge user's saved competitors with DEFAULT_COMPETITORS so 15-day scan always has a strong 12-channel pool
    const merged = Array.from(new Set([...saved, ...DEFAULT_COMPETITORS]));
    handles = merged.slice(0, 12);
  } else {
    handles = handles.slice(0, 12);
  }
  const seenSet = new Set((excludeIds || []).map(String));

  // 1) Resolve uploads playlist for each handle (1 quota unit each)
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

  // 2) Fetch last 35 uploads per channel (SAME 1 quota unit per channel!)
  // Used to calculate accurate channel median + catch every breakout in the last 15 days
  const vidTasks = chans.map(async (c) => {
    try {
      const r = await fetchWithTimeout(`https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId=${encodeURIComponent(c.uploads)}&maxResults=35&key=${encodeURIComponent(ytKey)}`, {}, 6500);
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

  // 3) Batch video stats + duration in parallel chunks of 50 (1 quota unit per 50 videos)
  const chunks = [];
  for (let off = 0; off < Math.min(allIds.length, 300); off += 50) {
    chunks.push(allIds.slice(off, off + 50));
  }
  const vBatches = await Promise.all(
    chunks.map(async (chunk) => {
      try {
        const vr = await fetchWithTimeout(`https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${chunk.join(",")}&key=${encodeURIComponent(ytKey)}`, {}, 7500);
        if (!vr.ok) return [];
        const vj = await vr.json();
        return vj.items || [];
      } catch (e) { return []; }
    })
  );
  const vItems = vBatches.flat();

  const now = Date.now();
  const strictAll = [];
  const relaxedAll = [];
  for (const v of vItems) {
    const dur = parseIsoDurationSec(v.contentDetails && v.contentDetails.duration);
    const pubMs = Date.parse((v.snippet && v.snippet.publishedAt) || "");
    const ageH = Math.max(6, (now - (pubMs || now)) / 3600000);
    const ageDays = Math.round(ageH / 24);
    // Keep up to 180d ONLY for accurate channel baseline median; final selection is strictly 15d (max 30d backup)
    if (ageDays > 180) continue;
    const vTitle = (v.snippet && v.snippet.title) || "Untitled";
    if (isBoringVlogTitle(vTitle)) continue;
    const views = Number((v.statistics && v.statistics.viewCount) || 0);
    if (views < 2000) continue;
    const meta = idMap.get(v.id) || {};
    const entry = {
      id: v.id,
      title: vTitle,
      channel: meta.channel || (v.snippet && v.snippet.channelTitle) || "",
      handle: meta.handle || "",
      catKey,
      fmt: isLongFmt ? "LONG" : "SHORT",
      views,
      dur,
      ageDays,
      velScore: views / Math.pow(ageH, 0.85),
      url: `https://www.youtube.com/watch?v=${v.id}`,
    };
    if (isLongFmt) {
      if (dur >= 240 && dur <= 2400) strictAll.push(entry);
      else if (dur >= 150 && dur <= 3600) relaxedAll.push(entry);
    } else {
      if (dur >= 12 && dur <= 95) strictAll.push(entry);
      else if (dur >= 12 && dur <= 180) relaxedAll.push(entry);
    }
  }
  const all = strictAll.length >= 6 ? strictAll : [...strictAll, ...relaxedAll];

  // 4) Accurate Channel Median & Breakout-First Scoring (v4.19)
  // Prevents brand-new 0.5x videos from beating genuine 3x-10x+ breakout hits!
  const byCh = new Map();
  for (const x of all) {
    const k = x.handle || x.channel;
    if (!byCh.has(k)) byCh.set(k, []);
    byCh.get(k).push(x.views);
  }
  const chMed = new Map();
  for (const [k, arr] of byCh.entries()) {
    arr.sort((a, b) => a - b);
    chMed.set(k, Math.max(2000, arr[Math.floor(arr.length / 2)] || 2000));
  }
  for (const x of all) {
    const med = chMed.get(x.handle || x.channel) || 10000;
    const mult = Math.max(0.2, x.views / med);
    x.outlierMult = Number(mult.toFixed(1));
    x.viralRating = Math.min(9.9, Math.max(5.0, Number((5.2 + Math.log2(mult + 0.5) * 1.85).toFixed(1))));
    const multWeight = Math.pow(Math.min(12.0, mult), 1.65);
    const scaleBoost = Math.log10(Math.max(1000, x.views));
    const recencyBoost = x.ageDays <= 7 ? 1.25 : (x.ageDays <= 15 ? 1.0 : 0.65);
    x.score = multWeight * scaleBoost * recencyBoost;
  }

  // 5) STRICT 15-DAY FRESH + BREAKOUT MULTIPLIER TIERS (v4.19)
  // Tier 1: Last 15 days AND >= 2.0x breakout (Gold!)
  // Tier 2: Last 15 days AND >= 1.3x strong performer (only if Tier 1 < 5)
  // Tier 3: Last 30 days AND >= 2.0x breakout backup (only if last 15d still < 5)
  // Tier 4: Last 30 days sorted by breakout multiplier (last resort, never old >30d unless empty)
  const fresh15 = all.filter(x => x.ageDays <= 15);
  const fresh30 = all.filter(x => x.ageDays <= 30);

  const pickTiered = (filterSeen) => {
    const ok = (x) => !filterSeen || !seenSet.has(x.id);
    const byScore = (a, b) => b.score - a.score;
    const t1 = fresh15.filter(x => x.outlierMult >= 2.0 && ok(x)).sort(byScore);
    const t2 = fresh15.filter(x => x.outlierMult >= 1.3 && x.outlierMult < 2.0 && ok(x)).sort(byScore);
    const t3 = fresh30.filter(x => x.ageDays > 15 && x.outlierMult >= 2.0 && ok(x)).sort(byScore);
    const t4 = fresh30.filter(x => x.outlierMult < 1.3 && ok(x)).sort((a, b) => (b.outlierMult - a.outlierMult) || (b.score - a.score));
    const ordered = [...t1, ...t2, ...t3, ...t4];
    if (ordered.length) return ordered;
    return all.filter(ok).sort(byScore);
  };

  let pool = pickTiered(true);
  // If unseen high-quality breakout items (<15d, >=1.3x) ran out, recycle 15-day breakouts instead of showing 0.5x junk!
  const unseenGood = pool.filter(x => x.ageDays <= 15 && x.outlierMult >= 1.3).length;
  const totalGood = fresh15.filter(x => x.outlierMult >= 1.3).length;
  const recycled = unseenGood < 3 && totalGood >= 3;
  if (recycled) {
    pool = pickTiered(false);
  } else if (pool.length < 3 && all.length > 0) {
    pool = pickTiered(false);
  }

  // Pick Top 5 diverse: prefer 1 per channel from strong breakouts first, then allow 2nd from same channel if it's >= 2.0x
  const picked = [];
  const chCount = new Map();
  for (const v of pool) {
    if (picked.length >= 5) break;
    const k = v.handle || v.channel;
    if ((chCount.get(k) || 0) === 0) {
      picked.push(v);
      chCount.set(k, 1);
    }
  }
  for (const v of pool) {
    if (picked.length >= 5) break;
    if (!picked.some(p => p.id === v.id)) {
      picked.push(v);
    }
  }
  // Keep final Top 5 cleanly ordered by highest breakout score
  picked.sort((a, b) => b.score - a.score);
  return { items: picked, recycled };
}

async function showTrendCategoryMenu(env, chatId, editMsgId = null, fmt = "SHORT") {
  const isLong = String(fmt || "SHORT").toUpperCase() === "LONG";
  const modeTag = isLong ? "L" : "S";
  const txt = isLong
    ? "🎬 /trends [LONG 5–6 min, 16:9] — Kis Category Ke Latest Viral Documentary Topics Scan Karun?\n\nNitish Rajput / Dhruv Rathee style strict 5–6 min (750–900 words) Hindi script + realistic newspaper/maps banenge:"
    : "⚡ /trends [SHORT 9:16, 45–55s] — Kis Category Ke Latest Viral Shorts Scan Karun?\n\n0–3s viral hook + full-screen visuals + exact '||' hints banenge (🔄 Refresh par hamesha 5 NAYE topics!):";
  const kb = {
    inline_keyboard: [
      [
        { text: isLong ? "⚡ Switch to SHORT (9:16)" : "✅ SHORT (9:16)", callback_data: "tr:fmt:SHORT" },
        { text: isLong ? "✅ LONG (5-6m 16:9)" : "🎬 Switch to LONG (5-6m)", callback_data: "tr:fmt:LONG" },
      ],
      [{ text: "🧠 Facts & Science", callback_data: `tr:cat:facts:${modeTag}` }, { text: "💼 Business & History", callback_data: `tr:cat:business:${modeTag}` }],
      [{ text: "🔥 Influencer News", callback_data: `tr:cat:influencer:${modeTag}` }, { text: "📱 Tech & AI Updates", callback_data: `tr:cat:tech:${modeTag}` }],
      [{ text: "🎬 Movies & Reviews", callback_data: `tr:cat:movies:${modeTag}` }, { text: "🌐 X/IG/FB Viral News", callback_data: `tr:cat:socialnews:${modeTag}` }],
      [{ text: "🌍 Mix All (Top Viral)", callback_data: `tr:cat:mix:${modeTag}` }],
    ],
  };
  if (editMsgId) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: editMsgId, text: txt, reply_markup: kb });
  } else {
    await tgApi(env, "sendMessage", { chat_id: chatId, text: txt, reply_markup: kb });
  }
}

async function runTrendsForCategory(env, chatId, catKey = "facts", isRefresh = false, editMsgId = null, fmt = "SHORT") {
  const isLongFmt = String(fmt || "SHORT").toUpperCase() === "LONG";
  const fmtLabel = isLongFmt ? "LONG 5–6m" : "SHORT 9:16";
  const cat = TREND_CATEGORIES[catKey] || TREND_CATEGORIES.facts;
  const waitTxt = `🔥 [${fmtLabel}] ${cat.label} ke ${isRefresh ? "NAYE viral topics" : "latest viral videos"} scan kar raha hoon (~5 sec)...`;
  let waitMsgId = editMsgId;
  if (waitMsgId) {
    await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsgId, text: waitTxt });
  } else {
    const waitRes = await tgApi(env, "sendMessage", { chat_id: chatId, text: waitTxt });
    waitMsgId = waitRes.ok ? ((await waitRes.json()).result || {}).message_id : null;
  }

  const cacheKey = `${catKey}_${isLongFmt ? "LONG" : "SHORT"}`;
  const prev = await readGhJson(env, TRENDS_CACHE_PATH, { items: [], seenByCat: {} });
  const seenByCat = (prev.data && prev.data.seenByCat && typeof prev.data.seenByCat === "object") ? { ...prev.data.seenByCat } : {};
  const prevSeen = Array.isArray(seenByCat[cacheKey]) ? seenByCat[cacheKey] : [];
  const prevIds = (prev.data && Array.isArray(prev.data.items) && prev.data.catKey === catKey && prev.data.fmt === (isLongFmt ? "LONG" : "SHORT"))
    ? prev.data.items.map(x => x.id).filter(Boolean) : [];
  const excludeIds = isRefresh ? Array.from(new Set([...prevSeen, ...prevIds])) : prevSeen;

  const scan = (catKey === "socialnews")
    ? await scanSocialNewsTrends(env, excludeIds, isLongFmt ? "LONG" : "SHORT")
    : await scanCompetitorTrends(env, catKey, excludeIds, isLongFmt ? "LONG" : "SHORT");
  const trends = scan.items || [];
  if (!trends.length) {
    const errTxt = (catKey === "socialnews")
      ? `❌ [${fmtLabel}] ${cat.label} ke news feeds abhi slow hain. 1 minute baad dobara try karein ya doosri category chunein.`
      : `❌ [${fmtLabel}] ${cat.label} me abhi koi fresh trending video nahi mili (YOUTUBE_KEY quota ya doosri category try karein).`;
    if (waitMsgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: waitMsgId, text: errTxt });
    else await tgReply(env.TG_TOKEN, chatId, errTxt, true);
    return;
  }

  const newIds = trends.map(v => v.id);
  seenByCat[cacheKey] = scan.recycled
    ? newIds
    : Array.from(new Set([...excludeIds, ...newIds])).slice(-50);

  const taggedTrends = trends.map(v => ({ ...v, fmt: isLongFmt ? "LONG" : "SHORT" }));
  await writeGhJson(env, TRENDS_CACHE_PATH, { items: taggedTrends, catKey, fmt: isLongFmt ? "LONG" : "SHORT", seenByCat, ts: Date.now() }, prev.sha, `trends ${cacheKey}`);

  const lines = [
    `🔥 [${fmtLabel}] ${cat.label} — Top 5 ${isRefresh ? "NAYE " : ""}15-Day Breakout Topics${scan.recycled ? " (Pool reset ✓)" : ""}:\n`,
  ];
  trends.forEach((v, i) => {
    const badge = v.outlierMult ? ` • 🔥 ${v.outlierMult}x (${v.viralRating}/10)` : "";
    lines.push(`${i + 1}️⃣ ${v.title.slice(0, 72)}\n   📺 ${v.channel} • 👁 ${fmtViews(v.views)} (${v.ageDays}d)${badge}\n   🔗 ${v.url}`);
  });
  lines.push(isLongFmt
    ? "\n👇 Number tap karo (STRICT 5–6 min Nitish/Dhruv style Hindi documentary script + realistic newspaper/maps hints banenge):"
    : "\n👇 Number tap karo (100% original Hindi Short script + viral hook + exact visuals hints banenge):");

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

  const isLongVideo = String((video && video.fmt) || "SHORT").toUpperCase() === "LONG";
  const curYear = new Date().getFullYear();
  const catRule = (TREND_CATEGORIES[(video && video.catKey) || "facts"] || TREND_CATEGORIES.facts).visualRule;
  const basePrompt = isLongVideo ? `You are India's #1 viral Hindi Documentary Scriptwriter (Dhruv Rathee / Nitish Rajput pacing) for "The Viral Gyaan".
TASK:
1) Study this viral topic and write a 100% ORIGINAL, 100% FACTUAL 5-to-6 minute Hindi YouTube Documentary script (~750-880 Hindi words, NEVER copy/translate, NEVER invent fake features or fake stats${rewrite ? " — use a COMPLETELY DIFFERENT opening hook and angle than before" : ""}).
2) Follow a smooth, continuous Viral Documentary Retention Flow (ZERO chapter headings!):
   - Cold Open Hook (0-25s) with high stakes & curiosity gap
   - Smooth transitions using spoken open loops (like "Par asli khel toh ab shuru hota hai...") — STRICT: NEVER write "अध्याय 1", "अध्याय 2", "भाग 1", "Chapter 1", or "## ..." headings anywhere in the script!
   - Real numbers, dates, proof & climax reveal
   - Short engaging comment-question CTA at the end
3) UNIVERSAL VISUAL HINT & DIGIT RULES (CRITICAL — FOLLOW FOR EVERY LINE):
   - STRICT LANGUAGE & FACT LOCK: Write ONLY in Hindi (Devanagari) + common English words — NEVER output Chinese/Bengali/Arabic/foreign script characters! NEVER invent fake people, fake spy names, or fake operations; use ONLY verified real facts from the reference video.\n   - CURRENT YEAR IS ${curYear}. NEVER refer to ${curYear - 2} as "this year" or outdated timelines. ALWAYS write ALL numbers & years in ENGLISH digits (e.g., 1999, ${curYear}, 10 Billion — NEVER Hindi digits like १९९९! NEVER use markdown ** bold asterisks!).
   - STRICT COUNTRY & PERSON ANCHOR (v4.18): Every single "||" hint MUST include the EXACT country/city/person/entity of that line (e.g., "pakistan karachi street protest crowd", "asim munir pakistan army general", NEVER bare "protest crowd", "flag waving", "military statue", "tv screen", "phone in hand", "new year 2025", "rock concert", "question mark", "subscribe animation").
   - SMART AUTO AI REALISTIC SCENES (v4.18): Whenever a non-celebrity line describes a rare, dramatic, or impossible-to-film visual (wildlife emotion/action like "grey wolf lovingly nuzzling wolf cubs snow forest" or "wolf leaping across snowy mountain cliff", feats of strength like "muscular strongman lifting heavy boulder arena dramatic lighting", ancient history, space/deep-sea), use "|| AI: <8-14 vivid photorealistic documentary words>" (up to 25% of lines — NEVER use "|| AI:" for real living politicians/celebrities!).
   - SMART AUTO 30FPS AI EXPLAINER (v4.18): Whenever a line explains HOW something works, a mechanism, process, anatomy, science/tech/finance/law/geopolitics breakdown, or comparison, add [explain: <clear visual mechanism/diagram to animate in 30fps>] BEFORE "||" (2-4 per Long script — NEVER on real living celebrities!).
   - MAP & CTA LIMITS: Use [map: Place, Country] AT MOST 2 times in the entire Long script (never repeat the same country!), [route: PlaceA -> PlaceB | Stat] for paths/flights/money flows, [news: Short Headline | Source] max 2-3 times. Last CTA line MUST end with "|| <cinematic hero closing visual of main topic>" (NEVER "tv screen" or "phone in hand"!).
${catRule}

OUTPUT FORMAT (strictly follow):
VISUAL_REFS:
- <visual reference 1>
- <visual reference 2>
- <visual reference 3>

SCRIPT:
LONG
MODE: <science | army | news | business | history | mystery | sports | influencer | technology | general>
TITLE: <45-60 char high-CTR Hindi SEO title> | <2-3 bold Hindi thumbnail words ONLY — NEVER add a 3rd pipe '|'>
<STRICT FORMAT — EVERY SINGLE SPOKEN LINE MUST END WITH " || <3-4 lowercase English camera words>"! NEVER start with "क्या आपने कभी सोचा है" or "चलिए शुरू करते हैं". Follow this exact pattern for all 42-55 lines (750-880 words total) with 3-5 [map:]/[news:]/[impact]/[ink] tags:>
2009 में NASA के ऑर्बिटर ने चाँद की सतह के नीचे एक रहस्यमयी गड्ढा पकड़ा! [impact] || nasa lunar orbiter crater closeup
यह गड्ढा Mare Tranquillitatis इलाके में मिला था। [map: Mare Tranquillitatis, Moon] || moon surface dark crater aerial
रिपोर्ट के मुताबिक इसके अंदर का तापमान हमेशा स्थिर रहता है। [news: NASA Confirms Subsurface Lunar Cave | NASA LRO] || lunar cave rocky interior shadows
... (continue 42-55 lines, EVERY line ending with " || <3-4 lowercase English camera words>") ...
इस पूरे मामले पर आपकी क्या राय है? कमेंट में ज़रूर बताएं और ऐसे ही रिसर्च वीडियो के लिए सब्सक्राइब करें। || <hero closing visual of main topic>`
  : `You are India's #1 viral Hindi YouTube Shorts Director for "The Viral Gyaan".
TASK:
1) Study this reference viral YouTube Short. Focus ONLY on the factual topic and WHAT REAL FOOTAGES, IMAGES, OBJECTS, PEOPLE, AND SCENES best explain it.
2) Write a 100% ORIGINAL, 100% FACTUAL Hindi YouTube Short script (40-55 sec) using the proven 4-Block Viral Retention Formula:
   - Line 1 (0-3s): Scroll-Stopper Curiosity/Shock Hook (a bold question or surprising fact that stops thumb-scroll in 2 seconds — ZERO slow intro, ZERO broken numbering, ZERO ** markdown!)
   - Lines 2-8: Fast Escalation with 2-3 concrete numbers/facts
   - Lines 9-14: Unexpected Twist / Big Reveal
   - Final Line: Ultra-short 2-sec CTA
   (NEVER copy/translate, and NEVER invent fake app features or fake stats${rewrite ? " — use a COMPLETELY DIFFERENT opening hook and angle than before" : ""}).
3) UNIVERSAL VISUAL HINT & DIGIT RULES (CRITICAL — FOLLOW FOR EVERY LINE):
   - STRICT LANGUAGE & FACT LOCK: Write ONLY in Hindi (Devanagari) + common English words — NEVER output Chinese/Bengali/foreign characters! NEVER invent fake names or fake facts.\n   - CURRENT YEAR IS ${curYear}. NEVER use outdated years like ${curYear - 2} as current! ALWAYS write ALL numbers & years in ENGLISH digits (e.g., 1999, ${curYear}, 15 Lakh, 230°C — NEVER Hindi digits like १९९९! NEVER use markdown ** bold!).
   - STRICT COUNTRY & PERSON ANCHOR (v4.18): Every single "||" hint MUST include the EXACT country/city/person/entity of that line (e.g., "pakistan karachi street protest", "grey wolf pack snow", "iphone 17 pro closeup" — NEVER bare "flag waving", "tv screen", "phone in hand", "statue", "rock concert", "new year balloons", "shocked face", "question mark", "subscribe animation").
   - SMART AUTO AI REALISTIC SCENES (v4.18): For rare/dramatic non-celebrity scenes where stock fails (wildlife emotion/action like "grey wolf lovingly nuzzling cubs snow forest" or "wolf leaping across mountain cliff", feats of strength like "giant muscular strongman lifting heavy man dramatic lighting", ancient/space/deep-sea scenes), use "|| AI: <8-14 vivid photorealistic words>" (NEVER for real living celebrities!).
   - SMART AUTO 30FPS AI EXPLAINER (v4.18): On 1-2 lines that explain HOW something works, a mechanism, comparison, or step-by-step concept, add [explain: <short mechanism/diagram to animate in 30fps>] BEFORE "||" (NEVER on real living celebrities!).
   - MAP & CTA LIMITS: Max 1 [map:] tag per Short (never repeat!), max 1-2 [news:]/[impact]/[ink] tags. Last Subscribe CTA line MUST end with "|| <hero closing visual of main topic>" (NEVER "tv screen" or "phone in hand"!).
${catRule}

OUTPUT FORMAT (strictly follow):
VISUAL_REFS:
- <visual reference 1>
- <visual reference 2>
- <visual reference 3>

SCRIPT:
MODE: <science | army | news | business | history | mystery | sports | influencer | technology | general>
TITLE: <45-60 char high-CTR Hindi SEO title> | <2-3 bold Hindi thumbnail words ONLY — NEVER add a 3rd pipe '|'>
<STRICT FORMAT — EVERY SINGLE SPOKEN LINE MUST END WITH " || <3-4 lowercase English camera words>"! Follow this exact pattern for all 14-17 lines with 2-3 [map:]/[news:]/[impact]/[ink] tags:>
क्या आप यकीन करेंगे कि समुद्र के 11 किलोमीटर नीचे भी ज़िंदगी मौजूद है? [impact] || deep ocean mariana trench submarine
वैज्ञानिकों ने यहाँ एक अनोखा जीव खोजा है। [news: New Deep Sea Species Found | NOAA] || glowing deep sea creature underwater
... (continue 14-17 short lines, EVERY line ending with " || <3-4 lowercase English camera words>") ...
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना। || <hero closing visual of main topic>`;

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
            if (out2) {
              const fixed2 = await repairMissingVisualHints(env, out2, isLongVideo, t0 + 27500);
              return { text: fixed2, mode: transcript ? "transcript" : "topic", model };
            }
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
    const groqRes = await callGroqTrendScript(env, fbPrompt, Boolean(transcript), errs, t0 + 22000);
    if (groqRes && groqRes.text) {
      groqRes.text = await repairMissingVisualHints(env, groqRes.text, isLongVideo, t0 + 28000);
      return groqRes;
    }
  }

  const gemErrs = errs.filter(e => !e.startsWith("groq")).slice(0, 4);
  const grqErrs = errs.filter(e => e.startsWith("groq")).slice(0, 4);
  const mergedErrs = [...gemErrs, ...grqErrs];
  return { text: "", error: (mergedErrs.length ? mergedErrs : errs.slice(0, 6)).join(" | ") };
}

const TRAP_VISUAL_HINT_RE = /\b(mockup|warning\s+screen|error\s+screen|settings\s+screen|scanning\s+code|code\s+graphic|graphic|animation\s+overlay|subscribe\s+button|bell\s+icon|infographic|diagram|cartoon|ui\s+screen|blocked\s+internet|shocked\s+face|question\s+mark|flag\s+waving|flag\s+tension|tension\s+visual|tv\s+screen|phone\s+in\s+hand|rock\s+concert|new\s+year|balloons|trophy|clipart|vector\s+icon|line\s+animation|rising\s+animation|flow\s+chart|falling\s+rain|deep\s+hole|world\s+map\s+showing|confused\s+man|calendar\s+page\s+flip|clock\s+ticking)\b/i;

function inspectVisualHints(rawText) {
  const txt = String(rawText || "");
  const idx = txt.indexOf("SCRIPT:");
  const body = idx >= 0 ? txt.slice(idx + 7) : txt;
  const spoken = body.split(/\r?\n/).map(l => l.trim()).filter(l =>
    l && !/^(LONG|SHORT|MODE:|TITLE:|##|#|VISUAL_REFS:|-\s)/i.test(l)
  );
  if (spoken.length < 4) return { total: spoken.length, withHint: spoken.length, weakCount: 0, needsRepair: false };
  let withHint = 0;
  let weakCount = 0;
  for (const line of spoken) {
    const hasExplain = /\[explain:/i.test(line);
    const hasNewsOrMap = /\[(news|map|route):/i.test(line);
    const parts = line.split("||");
    if (parts.length < 2 || !/[a-zA-Z0-9]{2,}/.test(parts[1])) {
      if (!hasExplain && !hasNewsOrMap) weakCount++;
      continue;
    }
    withHint++;
    const hint = parts[1].trim();
    if (/^AI\s*:/i.test(hint)) continue; // explicit photorealistic AI scene hint is valid
    const words = hint.split(/\s+/).filter(Boolean);
    const isTooLong = words.length > 6;
    const isTrap = TRAP_VISUAL_HINT_RE.test(hint);
    if ((isTooLong || isTrap) && !hasExplain && !hasNewsOrMap) {
      weakCount++;
    }
  }
  const explainCount = spoken.filter(l => /\[explain:/i.test(l)).length;
  const hasExplainableLine = spoken.some(l => /(कैसे|काम करता|सिस्टम|सर्वर|डेटा|तकनीक|सेंसर|कानून|नियम|ग्लिच|प्रोसेस|नेटवर्क|सॉफ्टवेयर|फॉरेंसिक|बैलिस्टिक|स्कैनर|सर्जरी|ट्यूमर|ट्रैक|फिंगरप्रिंट|स्याही|how|works|system|server|data|process|forensic|scanner|surgery|brain|law|rule)/i.test(l));
  const missingExplain = (explainCount === 0 && hasExplainableLine && spoken.length >= 6);
  const missingRatio = 1 - (withHint / spoken.length);
  const weakRatio = weakCount / spoken.length;
  const needsRepair = (missingRatio > 0.30) || (weakCount >= 2 && weakRatio >= 0.22) || missingExplain;
  return { total: spoken.length, withHint, weakCount, explainCount, missingExplain, needsRepair };
}

function hasEnoughVisualHints(rawText) {
  return !inspectVisualHints(rawText).needsRepair;
}

async function repairMissingVisualHints(env, rawText, isLongVideo, deadlineMs) {
  const audit = inspectVisualHints(rawText);
  if (!audit.needsRepair) return rawText;
  if (Date.now() > deadlineMs - 3200) return rawText;
  const groqKeys = getGroqKeys(env);
  if (!groqKeys.length) return rawText;
  const repairPrompt = `You are a VideoTool Visual Hint Doctor. Audit and upgrade the "|| <visual hint>" hints in the Hindi script below so our automated stock/YouTube/AI visual engine finds 100% sharp, relatable visuals on EVERY line!
STRICT RULES:
1) KEEP THE EXACT SAME HINDI STORY word-for-word, plus MODE:, TITLE: (max 2 parts separated by ONE '|'), and ${isLongVideo ? "LONG header" : "Short lines"}. Do NOT alter Hindi facts or dialogue.
2) Every spoken Hindi line MUST end with " || <3-5 simple lowercase real-world English camera words>" anchored to the exact country/city/person/object (searchable on YouTube/Pixabay/Pinterest).
3) REPLACE all weak, long (>6 words), or unsearchable hints (NEVER use "mockup", "warning screen", "settings screen", "graphic", "animation overlay", "subscribe button", "bell icon", "diagram", "cartoon", "shocked face", "flag waving", "tv screen", "phone in hand").
4) SMART AUTO ROUTING for hard-to-film scenes:
   - On ${isLongVideo ? "2-3" : "1-2"} lines explaining HOW a mechanism, surveillance, software, science, or rule works, put "[explain: clear 30fps animated diagram/mechanism]" BEFORE "||" (and a simple real-world fallback after "||").
   - On ${isLongVideo ? "3-5" : "1-2"} specific Indian/modern/rare non-celebrity scenes that free stock libraries like Pixabay do NOT have (e.g., Indian rooftop plastic water tank overflowing, electrician installing small water sensor on Indian roof, hidden microchip scanning phone, rare wildlife/historical action — NEVER living celebrities!), use " || AI: <8-12 vivid photorealistic documentary words>".
   - On cross-country loan/debt/trade/flight/geopolitics lines, add "[route: CityA, CountryA -> CityB, CountryB | Short Stat]" (30fps satellite map). On breaking/policy/court proof lines, add "[news: Short Headline | Credible Source]". On viral X/Twitter/social statement lines, add "[tweet: Name | @handle | Short quote]". Max ${isLongVideo ? "2" : "1"} "[map: Place, Country]" (no duplicates).
   - On the closing CTA line, use a clean topic-hero closing scene (NEVER "subscribe button" or "bell icon").
5) NEVER output Chinese/Bengali characters or ** bold markdown.
Return ONLY the upgraded script starting with SCRIPT:

INPUT SCRIPT:
${String(rawText || "").slice(0, 6500)}`;
  try {
    const rep = await callGroqTrendScript(env, repairPrompt, true, [], deadlineMs);
    if (rep && rep.text) {
      const repAudit = inspectVisualHints(rep.text);
      if (repAudit.weakCount < audit.weakCount || (audit.missingExplain && repAudit.explainCount > 0) || !repAudit.needsRepair) {
        const origIdx = String(rawText || "").indexOf("SCRIPT:");
        const origRefs = origIdx > 0 ? String(rawText || "").slice(0, origIdx).trim() : "";
        const repBody = rep.text.includes("SCRIPT:") ? rep.text.slice(rep.text.indexOf("SCRIPT:")).trim() : ("SCRIPT:\n" + rep.text.trim());
        return origRefs ? (origRefs + "\n\n" + repBody) : repBody;
      }
    }
  } catch (e) {}
  return rawText;
}

async function autoOptimizePastedScript(env, rawScript, isLongVideo) {
  try {
    const audit = inspectVisualHints(rawScript);
    if (!audit.needsRepair) return { script: rawScript, upgraded: false };
    const wrapped = "SCRIPT:\n" + String(rawScript || "").trim();
    const fixed = await repairMissingVisualHints(env, wrapped, isLongVideo, Date.now() + 8500);
    if (fixed && fixed !== wrapped) {
      const clean = fixed.includes("SCRIPT:") ? fixed.slice(fixed.indexOf("SCRIPT:") + 7).trim() : fixed.trim();
      if (clean.length >= Math.max(40, String(rawScript || "").trim().length * 0.65)) {
        return { script: clean, upgraded: true };
      }
    }
  } catch (e) {}
  return { script: rawScript, upgraded: false };
}

function devanagariToEngDigits(s) {
  return String(s || "").replace(/[०-९]/g, ch => String(ch.charCodeAt(0) - 0x0966));
}

function parseTrendGeminiOutput(raw) {
  let clean = devanagariToEngDigits(String(raw || "")).replace(/```[a-z]*\n?/gi, "").replace(/```/g, "").trim();
  // v3.98 FIX: Join accidental newlines before punctuation or '||' (prevents empty '।' lines that trigger voice glitches!)
  clean = clean.replace(/\r\n/g, "\n").replace(/\n+\s*([।.!?]+\s*\|\||\|\|)/g, " $1");
  // v4.25: Join accidental mid-sentence Hindi newlines (e.g., "हजारों\nलीटर पानी...")
  clean = clean.replace(/([\u0900-\u097F])\n+\s*([\u0900-\u097F])/g, "$1 $2");
  const idx = clean.indexOf("SCRIPT:");
  if (idx === -1) return { refs: "", script: clean };
  const refs = clean.slice(0, idx).replace(/VISUAL_REFS:/i, "").trim();
  let script = clean.slice(idx + 7).trim();
  // v4.15: sanitize accidental 3rd '|' or placeholder words like '3 शब्द' in TITLE:
  script = script.replace(/^TITLE:\s*(.+)$/im, (_, val) => {
    const parts = val.split("|").map(x => x.trim()).filter(x => x && !/^(\d+\s*शब्द|2-4\s*bold|bold\s*hindi)/i.test(x));
    return "TITLE: " + parts.slice(0, 2).join(" | ");
  });
  // v4.24: fix accidental single-Devanagari + Latin fused LLM typos (e.g. 'मaturity' -> 'maturity') so TTS reads cleanly
  const _DEV_TO_LAT = { "म": "m", "ब": "b", "प": "p", "क": "k", "स": "s", "र": "r", "त": "t", "ट": "t", "द": "d", "ड": "d", "न": "n", "ल": "l", "ग": "g", "फ": "f", "व": "v", "ह": "h", "ज": "j", "च": "c" };
  script = script.split("\n").map(ln => {
    const p = ln.split("||");
    p[0] = p[0].replace(/(^|\s)([\u0905-\u0939])([a-z]{3,})\b/g, (m, sp, dv, lat) => {
      const ch = _DEV_TO_LAT[dv];
      return ch ? (sp + ch + lat) : m;
    });
    return p.join("||");
  }).join("\n");
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

    if (data === "tr:menu") { await showTrendCategoryMenu(env, chatId, msgId, "SHORT"); return; }
    if (data.startsWith("tr:fmt:")) {
      const fmt = data.split(":")[2] === "LONG" ? "LONG" : "SHORT";
      await showTrendCategoryMenu(env, chatId, msgId, fmt);
      return;
    }
    if (data.startsWith("tr:cat:")) {
      const sp = data.split(":");
      const ck = sp[2] || "facts";
      const fmt = sp[3] === "L" ? "LONG" : "SHORT";
      await runTrendsForCategory(env, chatId, ck, false, msgId, fmt);
      return;
    }
    if (data === "tr:ref" || data.startsWith("tr:ref:")) {
      const sp = data.split(":");
      const ck = data.includes(":ref:") ? (sp[2] || "facts") : "facts";
      const prevC = await readGhJson(env, TRENDS_CACHE_PATH, {});
      const fmt = (prevC.data && prevC.data.fmt) || "SHORT";
      await runTrendsForCategory(env, chatId, ck, true, msgId, fmt);
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
      const cleanDraftScript = String(dr.data.script || "").replace(/\*{2,}/g, "");
      const isLongDraft = /^LONG\b/im.test(cleanDraftScript) || (dr.data.video && String(dr.data.video.fmt || "").toUpperCase() === "LONG");
      const runMode = isLongDraft ? "LONG" : "SHORT";
      const res = await enqueueOrStart(env, [{ script: cleanDraftScript, mode: runMode, ts: Date.now() }]);
      const reply = res.started > 0
        ? `🚀 Approved! ${runMode === "LONG" ? "LONG (5–6 min, 16:9)" : "SHORT (9:16)"} video cloud par shuru ho gayi hai!\nBante hi video + Cover + Story + Auto-Publish buttons yahin aayenge.`
        : (res.queued > 0
          ? `📋 Approved! Queue me lag gayi (queue: ${res.queueLen}). Pehli video khatam hote hi apne aap chalegi.`
          : `❌ GitHub render trigger fail (${LAST_GH_DISPATCH_ERR || "unknown"}).`);
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
    const fullPreview = `${badge}\n\n${parsed.refs ? "🎬 Visual References:\n" + parsed.refs + "\n\n" : ""}📝 ORIGINAL SCRIPT (Padh kar approve karo):\n\n${parsed.script}`;
    const approveKb = {
      inline_keyboard: [
        [{ text: "✅ Haan, Video Banao", callback_data: "tr:go" }],
        [{ text: "✏️ Dobara Likho", callback_data: "tr:rw" }, { text: "❌ Cancel", callback_data: "tr:no" }],
      ],
    };
    if (fullPreview.length <= 3850) {
      if (statusMsg) {
        await tgApi(env, "editMessageText", { chat_id: chatId, message_id: statusMsg.message_id, text: fullPreview, reply_markup: approveKb });
      } else {
        await tgApi(env, "sendMessage", { chat_id: chatId, text: fullPreview, reply_markup: approveKb });
      }
    } else {
      // v4.24: Split Long script cleanly into 2 Telegram messages at a newline so user reads the FULL 5-6 min script!
      let cut = fullPreview.lastIndexOf("\n", 3700);
      if (cut < 1800) cut = 3700;
      const part1 = fullPreview.slice(0, cut).trim() + "\n\n⬇️ (Part 1/2 — baaki script neeche dekhein)";
      const part2 = "📄 (Part 2/2 — Script continue)\n\n" + fullPreview.slice(cut).trim();
      if (statusMsg) {
        await tgApi(env, "editMessageText", { chat_id: chatId, message_id: statusMsg.message_id, text: part1.slice(0, 3950) });
      } else {
        await tgApi(env, "sendMessage", { chat_id: chatId, text: part1.slice(0, 3950) });
      }
      await tgApi(env, "sendMessage", { chat_id: chatId, text: part2.slice(0, 3950), reply_markup: approveKb });
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
  const kb = buildPublishKeyboard(id, isLong);

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
            "Accept-Ranges": "none",
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
      "Accept-Ranges": "none",
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

async function publishFacebookPageStory(pageId, pageToken, storyBridgeUrl) {
  if (!storyBridgeUrl) return "";
  try {
    // Official Meta Facebook Page Photo Stories 2-step flow:
    // Step 1: Upload unpublished photo to Page
    const p1 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/photos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: storyBridgeUrl, published: false, access_token: pageToken }),
    }, 12000);
    const pj1 = await p1.json();
    if (!p1.ok || !pj1.id) {
      return `⚠️ FB Story photo fail: ${(pj1.error && pj1.error.message) || p1.status}`;
    }
    // Step 2: Publish photo as Facebook Page Story
    const p2 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/photo_stories`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ photo_id: pj1.id, access_token: pageToken }),
    }, 12000);
    const pj2 = await p2.json();
    if (p2.ok && (pj2.success || pj2.post_id)) {
      return "✅ Facebook Page Story Published!";
    }
    return `⚠️ FB Story publish fail: ${(pj2.error && pj2.error.message) || p2.status}`;
  } catch (e) {
    return `⚠️ FB Story error: ${String(e).slice(0, 90)}`;
  }
}

async function publishFacebookPage(env, item) {
  const sysToken = (env.META_ACCESS_TOKEN || "").trim();
  const pageId = (env.FB_PAGE_ID || "").trim();
  if (!sysToken || !pageId) return { ok: false, msg: "⚠️ FB skip: Cloudflare me META_ACCESS_TOKEN aur FB_PAGE_ID add karo." };
  const notes = [];
  let mainOk = false;
  try {
    const pageToken = await getFacebookPageToken(sysToken, pageId);
    const primaryMediaUrl = buildMetaMediaUrl(item.mode === "SHORT" ? item.tg_file_id : "", item.video_url, "mp4") || item.video_url;
    const backupMediaUrl = (item.mode === "SHORT" && item.tg_file_id)
      ? buildMetaMediaUrl(item.tg_file_id, item.video_url, "mp4", false)
      : "";
    const coverBridgeUrl = buildMetaMediaUrl(item.cover_tg_file_id, item.cover_url, "jpg");
    const storyBridgeUrl = buildMetaMediaUrl(item.story_tg_file_id, item.story_url, "jpg");

    if (item.mode === "LONG") {
      const vidBody = {
        file_url: primaryMediaUrl,
        title: item.title,
        description: item.ig_caption || item.description || item.title,
        access_token: pageToken,
      };
      const r = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/videos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(vidBody),
      }, 22000);
      const j = await r.json();
      if (r.ok && j.id) {
        mainOk = true;
        notes.push(`✅ Facebook Video Published (ID: ${j.id})`);
      } else {
        notes.push(`❌ FB Video error: ${(j.error && j.error.message) || r.status}`);
      }
    } else {
      // SHORT -> Official Facebook Page Reels 3-step URL flow (with Page Access Token + backup URL fallback!)
      const s1 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/video_reels`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_phase: "start", access_token: pageToken }),
      }, 12000);
      const j1 = await s1.json();
      if (!s1.ok || !j1.video_id) {
        notes.push(`❌ FB Reel start fail: ${(j1.error && j1.error.message) || s1.status}`);
      } else {
        let s2 = await fetchWithTimeout(`https://rupload.facebook.com/video-upload/${GRAPH_VER}/${j1.video_id}`, {
          method: "POST",
          headers: { Authorization: `OAuth ${pageToken}`, file_url: primaryMediaUrl },
        }, 18000);
        // If primary proxy URL failed on rupload, automatically retry once via Telegram file bridge!
        if (!s2.ok && backupMediaUrl && backupMediaUrl !== primaryMediaUrl) {
          s2 = await fetchWithTimeout(`https://rupload.facebook.com/video-upload/${GRAPH_VER}/${j1.video_id}`, {
            method: "POST",
            headers: { Authorization: `OAuth ${pageToken}`, file_url: backupMediaUrl },
          }, 18000);
        }
        if (!s2.ok) {
          const t2 = await s2.text();
          notes.push(`❌ FB Reel upload fail: ${t2.slice(0, 120)}`);
        } else {
          // Give Meta rupload 2.5s to finalize ingestion before finish phase
          await new Promise(r => setTimeout(r, 2500));
          const s3 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${pageId}/video_reels`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              upload_phase: "finish",
              video_id: j1.video_id,
              video_state: "PUBLISHED",
              title: (item.title || "").slice(0, 250),
              description: item.ig_caption || item.title,
              access_token: pageToken,
            }),
          }, 12000);
          const j3 = await s3.json();
          if (s3.ok && (j3.success || j3.post_id)) {
            mainOk = true;
            let coverNote = "";
            // Best-effort custom Reel Cover/Thumbnail attachment (silent fallback if Page restricts custom reel thumbs)
            if (coverBridgeUrl) {
              try {
                const th = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${j1.video_id}/thumbnails`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ url: coverBridgeUrl, is_preferred: true, access_token: pageToken }),
                }, 8000);
                if (th.ok) coverNote = " (+ Cover)";
              } catch (e) {}
            }
            notes.push(`✅ Facebook Page Reel${coverNote} Published!`);
          } else {
            notes.push(`❌ FB Reel finish fail: ${(j3.error && j3.error.message) || s3.status}`);
          }
        }
      }
    }

    // Publish Facebook Page Designer Story if story image exists
    if (storyBridgeUrl) {
      const stNote = await publishFacebookPageStory(pageId, pageToken, storyBridgeUrl);
      if (stNote) notes.push(stNote);
    }
    return { ok: mainOk, msg: notes.join("\n") };
  } catch (e) {
    notes.push(`❌ FB error: ${String(e).slice(0, 120)}`);
    return { ok: false, msg: notes.join("\n") };
  }
}

async function pollIgContainerStatus(cid, token, maxAttempts = 4, delayMs = 3000) {
  let lastCode = "IN_PROGRESS";
  let lastStatus = "";
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(r => setTimeout(r, delayMs));
    try {
      const st = await fetchWithTimeout(
        `https://graph.facebook.com/${GRAPH_VER}/${cid}?fields=status_code,status&access_token=${encodeURIComponent(token)}`,
        {},
        8000
      );
      if (st.ok) {
        const sj = await st.json();
        lastCode = String(sj.status_code || "IN_PROGRESS").toUpperCase();
        lastStatus = String(sj.status || "");
        if (lastCode === "FINISHED" || lastCode === "PUBLISHED") {
          return { status: "ready", code: lastCode, detail: lastStatus };
        }
        if (lastCode === "ERROR" || lastCode === "EXPIRED") {
          return { status: "meta_error", code: lastCode, detail: lastStatus || `Meta ${lastCode}` };
        }
      }
    } catch (e) {}
  }
  return { status: "pending", code: lastCode, detail: lastStatus };
}

async function publishInstagramReelAndStory(env, item) {
  const token = (env.META_ACCESS_TOKEN || "").trim();
  const igId = (env.IG_USER_ID || "").trim();
  if (!token || !igId) return { ok: false, msg: "⚠️ IG skip: Cloudflare me META_ACCESS_TOKEN aur IG_USER_ID add karo." };
  const notes = [];
  let pendingContainer = null;

  // 1) Create, Poll Status & Publish Designer Instagram Story (v4.21: waits for FINISHED instead of blind 2.5s!)
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
        const stPoll = await pollIgContainerStatus(sj1.id, token, 3, 2500);
        if (stPoll.status === "meta_error") {
          notes.push(`⚠️ IG Story fail (${stPoll.code}): ${stPoll.detail.slice(0, 90)}`);
        } else {
          const st2 = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media_publish`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ creation_id: sj1.id, access_token: token }),
          }, 10000);
          const sj2 = await st2.json();
          notes.push(st2.ok && sj2.id ? "✅ IG Designer Story Published!" : `⚠️ IG Story pending/err: ${(sj2.error && sj2.error.message) || st2.status}`);
        }
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
      return { status: "create_fail", err: (j1.error && j1.error.message) || String(r1.status), withCover: includeCover };
    }
    const cid = j1.id;
    const poll = await pollIgContainerStatus(cid, token, 4, 3500);
    if (poll.status === "ready") return { status: "ready", cid, withCover: includeCover };
    if (poll.status === "meta_error") return { status: "meta_error", err: poll.detail, withCover: includeCover };
    return { status: "pending", cid, withCover: includeCover };
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
      const covLbl = res.withCover && coverBridgeUrl ? " (+ Cover)" : "";
      notes.push(pub.ok && pj.id ? `✅ Instagram Reel${covLbl} Published!` : `❌ IG Publish fail: ${(pj.error && pj.error.message) || pub.status}`);
    } else if (res.status === "pending") {
      pendingContainer = res.cid;
      notes.push("⏳ Instagram video abhi Meta par process ho raha hai — 15–20 sec baad neeche '🔄 Complete IG Reel Publish' dabao!");
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

    if (action === "auto_sched") {
      await scheduleVideoAuto(env, chatId, msgId, id);
      return;
    }
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

    // Complete delayed IG Reel container publish (v4.21: checks Meta status_code FIRST!)
    if (action === "igfin") {
      const cid = parts[3] || "";
      const token = (env.META_ACCESS_TOKEN || "").trim();
      const igId = (env.IG_USER_ID || "").trim();
      const poll = await pollIgContainerStatus(cid, token, 2, 2500);
      if (poll.status === "pending") {
        await tgApi(env, "sendMessage", {
          chat_id: chatId,
          text: `⏳ Instagram video Meta par abhi bhi process ho raha hai (${poll.code}). 15–20 sec baad dobara dabao:`,
          reply_markup: { inline_keyboard: [[{ text: "🔄 Complete IG Reel Publish", callback_data: `pub:${id}:igfin:${cid}` }]] },
        });
        return;
      }
      if (poll.status === "meta_error") {
        await tgApi(env, "sendMessage", {
          chat_id: chatId,
          text: `❌ Meta ne yeh Reel container reject/expire kar diya (${poll.code}): ${poll.detail || "processing error"}\n👇 Neeche '📸 Sirf IG Retry' dabao (fresh container + auto-fallback):`,
          reply_markup: { inline_keyboard: [[{ text: "📸 Sirf IG Retry", callback_data: `pub:${id}:ig_only` }]] },
        });
        return;
      }
      const pub = await fetchWithTimeout(`https://graph.facebook.com/${GRAPH_VER}/${igId}/media_publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creation_id: cid, access_token: token }),
      }, 12000);
      const pj = await pub.json();
      if (pub.ok && pj.id) {
        await tgReply(env.TG_TOKEN, chatId, "✅ Instagram Reel (+ Cover) Published!", false);
      } else {
        await tgApi(env, "sendMessage", {
          chat_id: chatId,
          text: `❌ IG Publish error: ${(pj.error && pj.error.message) || pub.status}\n👇 Neeche '📸 Sirf IG Retry' dabao:`,
          reply_markup: { inline_keyboard: [[{ text: "📸 Sirf IG Retry", callback_data: `pub:${id}:ig_only` }]] },
        });
      }
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

    const doYt = (action === "yt" || action === "all" || action === "yt_pub" || action === "all_pub" || action === "yt_sched" || action === "all_sched");
    const doFb = (action === "meta" || action === "all" || action === "all_pub" || action === "all_sched" || action === "fb_only");
    const doIg = (action === "meta" || action === "all" || action === "all_pub" || action === "all_sched" || action === "ig_only");
    const ytPrivacy = (action === "yt_sched" || action === "all_sched")
      ? "scheduled"
      : ((action === "yt_pub" || action === "all_pub") ? "public" : "unlisted");

    // v4.07 PARALLEL EXECUTION: Run YouTube + Facebook + Instagram simultaneously (~15s total, never hits 30s CF timeout!)
    const ytTask = doYt ? (async () => {
      let ytVideoUrl = item.video_url
        ? (item.tg_file_id ? `${item.video_url}#vg_tg=${item.tg_file_id}` : item.video_url)
        : (item.tg_file_id ? `tgfile://${item.tg_file_id}` : "");
      if (item.cover_tg_file_id) ytVideoUrl += `#vg_th_tg=${item.cover_tg_file_id}`;
      if (item.cover_url) ytVideoUrl += `#vg_th_url=${encodeURIComponent(item.cover_url)}`;
      const ok = await dispatchGH(env, "publish_video.yml", {
        video_url: ytVideoUrl,
        title: item.title,
        description: item.description,
        tags: item.tags,
        mode: item.mode,
        category: item.category,
        privacy: ytPrivacy,
      });
      const privLbl = ytPrivacy === "scheduled" ? "25m Auto-PUBLIC ⏱️" : (ytPrivacy === "public" ? "PUBLIC 🚀" : "Unlisted 🔒");
      return ok
        ? `▶️ YouTube (${privLbl}): Upload shuru ho gaya (~1 min me link yahin aayega!)`
        : `❌ YouTube trigger fail (${LAST_GH_DISPATCH_ERR || "unknown error"}). Agar 401/403 ho to Cloudflare me GH_TOKEN refresh karein.`;
    })() : Promise.resolve(null);

    const fbTask = doFb ? publishFacebookPage(env, item) : Promise.resolve(null);

    const igTask = doIg ? (
      item.mode !== "LONG"
        ? publishInstagramReelAndStory(env, item)
        : Promise.resolve({ ok: true, msg: "ℹ️ Long (16:9) video ke liye Instagram Reels auto-skip kiya gaya." })
    ) : Promise.resolve(null);

    const [ytMsg, fbRes, igRes] = await Promise.all([ytTask, fbTask, igTask]);
    if (ytMsg) report.push(ytMsg);
    if (fbRes) report.push(fbRes.msg);
    if (igRes) {
      report.push(igRes.msg);
      if (igRes.pendingContainer) pendingIgCid = igRes.pendingContainer;
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
        { text: "📸 Sirf IG Retry", callback_data: `pub:${id}:ig_only` },
        { text: "📱 FB + IG Retry", callback_data: `pub:${id}:meta` },
      ]);
      retryRows.push([
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

// v4.30: /vmode AI CINEMATIC DOCUMENTARY MODE (DEFAULT ON) vs STOCK SEARCH SWITCH
async function getVmodeAiEnabled(env) {
  const cur = await readGhJson(env, SETTINGS_PATH, []);
  const arr = Array.isArray(cur.data) ? cur.data : [];
  // Default ON unless user explicitly selected Purana Stock Mode ("vmode_stock")
  return { enabled: !arr.includes("vmode_stock"), arr, sha: cur.sha };
}

async function setVmodeState(env, chatId, enableAi) {
  const st = await getVmodeAiEnabled(env);
  const next = st.arr.filter(x => x !== "vmode_ai" && x !== "vmode_stock");
  if (enableAi) next.push("vmode_ai");
  else next.push("vmode_stock");
  await writeGhJson(env, SETTINGS_PATH, next, st.sha, `vmode ${enableAi ? "ai" : "stock"}`);
  const msg = enableAi
    ? "🎬 Visual Mode: AI CINEMATIC DOCUMENTARY ON ⭐ (Default)\n\nAb har video mein automatic ultra-realistic 35mm AI scenes + fast 2-2.5s cuts + 30fps AI Explainer + real Wikimedia portraits (celebrities ke liye) banenge!\n(Stock mode chahiye ho toh kabhi bhi /vmode stock dabaein.)"
    : "🔎 Visual Mode: PURANA STOCK SEARCH ON\n\nAb Pixabay + YouTube + Wikimedia stock search chalega (AI fallback backup ke saath).\n(Wapas AI Cinematic Mode ke liye kabhi bhi /vmode ai dabaein.)";
  await tgReply(env.TG_TOKEN, chatId, msg, true);
}

async function showVmodeMenu(env, chatId) {
  const st = await getVmodeAiEnabled(env);
  await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: `🎬 Visual Mode abhi: ${st.enabled ? "✨ AI CINEMATIC DOCUMENTARY (Default ON ⭐)" : "🔎 PURANA STOCK SEARCH (Pixabay + YouTube)"}\n\nKaunsa mode chalu rakhna hai?`,
    reply_markup: {
      inline_keyboard: [[
        { text: "✨ AI Cinematic Mode (Default ⭐)", callback_data: "vm:ai" },
        { text: "🔎 Purana Stock Mode", callback_data: "vm:stock" },
      ]],
    },
  });
}

async function handleVmodeCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const enableAi = cq.data === "vm:ai";
  await setVmodeState(env, chatId, enableAi);
}


// =========================================================================
// v4.05: 1-TAP RE-UPLOAD / RE-PUBLISH VAULT (/republish, /publish, Video Forward)
// =========================================================================
function buildPublishKeyboard(id, isLong) {
  return isLong ? {
    inline_keyboard: [
      [{ text: "📅 Auto-Schedule (3/Day Best IST ⭐)", callback_data: `pub:${id}:auto_sched` }],
      [{ text: "⏱️ YT 25m Auto-Public + FB Page (Turant)", callback_data: `pub:${id}:all_sched` }],
      [{ text: "🚀 YT Instant PUBLIC + FB Page", callback_data: `pub:${id}:all_pub` }],
      [{ text: "⏱️ YT 25m Auto-Public", callback_data: `pub:${id}:yt_sched` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf Facebook Page", callback_data: `pub:${id}:meta` }, { text: "❌ Skip", callback_data: `pub:${id}:skip` }],
    ],
  } : {
    inline_keyboard: [
      [{ text: "📅 Auto-Schedule (3/Day Best IST ⭐)", callback_data: `pub:${id}:auto_sched` }],
      [{ text: "⏱️ Sab Par (YT 25m Auto-Public + FB + IG ⭐)", callback_data: `pub:${id}:all_sched` }],
      [{ text: "🚀 Sab Par Instant PUBLIC (YT + FB + IG)", callback_data: `pub:${id}:all_pub` }],
      [{ text: "⏱️ YT 25m Auto-Public", callback_data: `pub:${id}:yt_sched` }, { text: "🔒 YT Unlisted", callback_data: `pub:${id}:yt` }],
      [{ text: "📱 Sirf FB + IG", callback_data: `pub:${id}:meta` }, { text: "📸 Sirf IG", callback_data: `pub:${id}:ig_only` }],
      [{ text: "❌ Skip", callback_data: `pub:${id}:skip` }],
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


// =========================================================================
// v4.10: AUTO-PILOT VIRAL PLANNER (/planner) + WINNER-LOCK + AUTO-PIVOT + CRON
// =========================================================================
const PLANNER_PATH = "seekha/planner_stats.json";

function computePlannerInsights(data) {
  const entries = Array.isArray(data && data.entries) ? data.entries : [];
  const byCat = {};
  for (const e of entries) {
    const c = e.cat || "facts";
    if (!byCat[c]) byCat[c] = [];
    byCat[c].push(Number(e.views || 0));
  }
  const catStats = {};
  let allViews = [];
  for (const [c, arr] of Object.entries(byCat)) {
    const avg = arr.reduce((a, b) => a + b, 0) / Math.max(1, arr.length);
    const recent3 = arr.slice(-3);
    const recAvg = recent3.reduce((a, b) => a + b, 0) / Math.max(1, recent3.length);
    const peak = Math.max(...arr);
    catStats[c] = { count: arr.length, avg: Math.round(avg), recAvg: Math.round(recAvg), peak };
    allViews = allViews.concat(arr);
  }
  const overallAvg = allViews.length ? Math.round(allViews.reduce((a, b) => a + b, 0) / allViews.length) : 0;

  let winner = (data && data.manualLock) || "";
  if (!winner && overallAvg > 0) {
    const ranked = Object.entries(catStats).sort((a, b) => b[1].avg - a[1].avg);
    if (ranked.length && ranked[0][1].avg >= overallAvg * 1.8 && ranked[0][1].count >= 2) {
      winner = ranked[0][0];
    }
  }

  let pivotAlert = "";
  if (winner && catStats[winner] && catStats[winner].count >= 3) {
    const st = catStats[winner];
    if (st.avg > 0 && st.recAvg <= st.avg * 0.60) {
      const nextBest = Object.entries(catStats)
        .filter(([c]) => c !== winner)
        .sort((a, b) => b[1].recAvg - a[1].recAvg)[0];
      const nextLbl = nextBest ? (TREND_CATEGORIES[nextBest[0]]?.label || nextBest[0]) : "📱 Tech & Gadgets / 💼 Business";
      pivotAlert = `🚨 AUTO-PIVOT ALERT: "${TREND_CATEGORIES[winner]?.label || winner}" ke aakhri 3 videos ke views 40%+ gir gaye (avg ${st.avg} -> recent ${st.recAvg})!\n👉 Agli best category try karo: ${nextLbl}`;
    }
  }

  return { winner, overallAvg, catStats, pivotAlert, total: entries.length };
}

async function handlePlannerCommand(env, chatId, rawText) {
  const parts = rawText.trim().split(/\s+/);
  const sub = (parts[1] || "").toLowerCase();
  const cur = await readGhJson(env, PLANNER_PATH, { entries: [], manualLock: "" });
  const data = (cur.data && typeof cur.data === "object") ? { entries: cur.data.entries || [], manualLock: cur.data.manualLock || "" } : { entries: [], manualLock: "" };

  if (sub === "log" && parts.length >= 5) {
    const cat = parts[2].toLowerCase();
    const plat = parts[3].toLowerCase();
    const views = Math.max(0, parseInt(parts[4], 10) || 0);
    if (!TREND_CATEGORIES[cat]) {
      await tgReply(env.TG_TOKEN, chatId, "⚠️ Valid categories: facts, tech, movies, updates, business", false);
      return;
    }
    data.entries.push({ ts: Date.now(), cat, plat, views });
    data.entries = data.entries.slice(-120);
    await writeGhJson(env, PLANNER_PATH, data, cur.sha, `planner log ${cat} ${plat} ${views}`);
    const ins = computePlannerInsights(data);
    let msg = `✅ Logged: ${TREND_CATEGORIES[cat].label} (${plat}) = ${views} views!\n`;
    if (ins.winner) msg += `🏆 Active Winner Category: ${TREND_CATEGORIES[ins.winner]?.label || ins.winner} (70-80% daily focus)\n`;
    if (ins.pivotAlert) msg += `\n${ins.pivotAlert}`;
    await tgReply(env.TG_TOKEN, chatId, msg, true);
    return;
  }

  if (sub === "lock" && parts[2]) {
    const cat = parts[2].toLowerCase();
    if (!TREND_CATEGORIES[cat]) {
      await tgReply(env.TG_TOKEN, chatId, "⚠️ Valid categories: facts, tech, movies, updates, business", false);
      return;
    }
    data.manualLock = cat;
    await writeGhJson(env, PLANNER_PATH, data, cur.sha, `planner lock ${cat}`);
    await tgReply(env.TG_TOKEN, chatId, `🏆 Winner Category manually locked: ${TREND_CATEGORIES[cat].label}\nAb daily 9 AM Shorts me 70-80% topics isi category par aayenge!`, true);
    return;
  }

  if (sub === "unlock") {
    data.manualLock = "";
    await writeGhJson(env, PLANNER_PATH, data, cur.sha, "planner unlock");
    await tgReply(env.TG_TOKEN, chatId, "🔓 Manual Winner Lock hata diya — ab auto 2x+ Winner detection chalu hai!", true);
    return;
  }

  const ins = computePlannerInsights(data);
  const lines = [
    "📈 VIRAL GYAAN AUTO-PILOT PLANNER (v4.10)",
    `🏆 Active Winner: ${ins.winner ? (TREND_CATEGORIES[ins.winner]?.label || ins.winner) : "Auto-detecting (abhi 🧠 Facts & Science default)"}`,
    `📊 Tracked Videos: ${ins.total} | Overall Avg: ${ins.overallAvg} views`,
    "",
  ];
  for (const [c, st] of Object.entries(ins.catStats)) {
    lines.push(`• ${TREND_CATEGORIES[c]?.label || c}: avg ${st.avg} (last 3: ${st.recAvg}, peak: ${st.peak}, n=${st.count})`);
  }
  if (!ins.total) {
    lines.push("ℹ️ Views log karne ka 1-line format:\n/planner log facts yt_short 1200\n/planner log tech ig 450");
  }
  if (ins.pivotAlert) {
    lines.push("", ins.pivotAlert);
  }
  lines.push("", "⏰ Auto Schedule (Cloudflare Cron): Daily 9 AM IST (5 Shorts) • Tue/Thu/Sun 5 PM IST (5 Long 5-6m)");

  const kb = {
    inline_keyboard: [
      [{ text: "⚡ Aaj ke 5 Shorts Topics", callback_data: "pl:shorts" }, { text: "🎬 5 Long (5-6m) Topics", callback_data: "pl:long" }],
      [{ text: "🏆 Lock Facts/Science", callback_data: "pl:lock:facts" }, { text: "🔓 Auto Mode", callback_data: "pl:unlock" }],
    ],
  };
  await tgApi(env, "sendMessage", { chat_id: chatId, text: lines.join("\n").slice(0, 3900), reply_markup: kb });
}

async function handlePlannerCallback(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const parts = (cq.data || "").split(":");
  const act = parts[1] || "";
  if (act === "shorts") {
    await runAutoPilotCron(env, "30 3 * * *", chatId);
    return;
  }
  if (act === "long") {
    await runAutoPilotCron(env, "30 11 * * 0,2,4", chatId);
    return;
  }
  if (act === "lock" && parts[2]) {
    await handlePlannerCommand(env, chatId, `/planner lock ${parts[2]}`);
    return;
  }
  if (act === "unlock") {
    await handlePlannerCommand(env, chatId, "/planner unlock");
  }
}

async function runAutoPilotCron(env, cronExpr, overrideChatId = "") {
  const chatId = String(overrideChatId || env.ALLOWED_CHAT_ID || "").trim();
  if (!chatId || !env.TG_TOKEN) return;
  const cur = await readGhJson(env, PLANNER_PATH, { entries: [], manualLock: "" });
  const ins = computePlannerInsights(cur.data || {});
  const isLongCron = String(cronExpr || "").includes("11") || String(cronExpr || "").toLowerCase().includes("long");
  const targetCat = isLongCron ? "mix" : (ins.winner || "facts");

  if (ins.pivotAlert) {
    await tgReply(env.TG_TOKEN, chatId, ins.pivotAlert, false);
  }
  const intro = isLongCron
    ? "🎬 AUTO-PILOT LONG VIDEO RADAR (5–6 min, 16:9 — Tue/Thu/Sun 5 PM IST)\nAaj ke Top 5 Viral Documentary Topics nikaal raha hoon..."
    : `🌅 GOOD MORNING! DAILY AUTO-PILOT SHORTS RADAR (9:00 AM IST)\n🏆 Focus Category: ${TREND_CATEGORIES[targetCat]?.label || targetCat}`;
  await tgReply(env.TG_TOKEN, chatId, intro, false);
  await runTrendsForCategory(env, chatId, targetCat, true, null, isLongCron ? "LONG" : "SHORT");
}


// =========================================================================
// v4.34: SMART 3-VIDEOS/DAY AUTO-SCHEDULER (9:00 AM, 1:30 PM, 7:00 PM IST)
// =========================================================================
const SCHED_PUB_PATH = "seekha/publish_schedule.json";
const IST_OFFSET_MS = 5.5 * 3600 * 1000;
const DAILY_SLOTS_IST = [
  { h: 9, m: 0, label: "9:00 AM IST" },
  { h: 13, m: 30, label: "1:30 PM IST" },
  { h: 19, m: 0, label: "7:00 PM IST" },
];

function findNextFreeIstSlot(existingPending, nowMs = Date.now()) {
  const taken = new Set(existingPending.map(x => Number(x.slot_utc_ms || 0)));
  const minAllowed = nowMs + 15 * 60 * 1000;
  const istNow = new Date(nowMs + IST_OFFSET_MS);
  const baseYear = istNow.getUTCFullYear();
  const baseMonth = istNow.getUTCMonth();
  const baseDay = istNow.getUTCDate();
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  for (let dOff = 0; dOff < 45; dOff++) {
    for (const sl of DAILY_SLOTS_IST) {
      const slotIstWallMs = Date.UTC(baseYear, baseMonth, baseDay + dOff, sl.h, sl.m, 0, 0);
      const slotUtcMs = slotIstWallMs - IST_OFFSET_MS;
      if (slotUtcMs < minAllowed) continue;
      let clash = false;
      for (const tk of taken) {
        if (Math.abs(tk - slotUtcMs) < 10 * 60 * 1000) { clash = true; break; }
      }
      if (!clash) {
        const dt = new Date(slotIstWallMs);
        const dayStr = `${days[dt.getUTCDay()]}, ${dt.getUTCDate()} ${months[dt.getUTCMonth()]} — ${sl.label}`;
        return { slot_utc_ms: slotUtcMs, slot_ist: dayStr };
      }
    }
  }
  const fb = nowMs + 24 * 3600 * 1000;
  return { slot_utc_ms: fb, slot_ist: "Tomorrow 9:00 AM IST" };
}

async function scheduleVideoAuto(env, chatId, msgId, id) {
  const store = await readGhJson(env, PUB_PATH, {});
  const item = store.data && store.data[id];
  if (!item || (!item.video_url && !item.tg_file_id)) {
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "⚠️ Ye publish card purana ho gaya — /republish se dobara kholein." });
    return;
  }
  const qCur = await readGhJson(env, SCHED_PUB_PATH, []);
  const queue = Array.isArray(qCur.data) ? qCur.data : [];
  const pending = queue.filter(x => x && x.status === "pending");
  const already = pending.find(x => x.id === id);
  if (already) {
    if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: `📅 Ye video pehle se scheduled hai!\n⏰ ${already.slot_ist}\n🎬 ${String(item.title || "").slice(0, 75)}` });
    return;
  }
  const slot = findNextFreeIstSlot(pending, Date.now());
  const entry = {
    id: item.id,
    title: String(item.title || "The Viral Gyaan").slice(0, 100),
    description: String(item.description || "").slice(0, 2000),
    tags: item.tags || "",
    mode: item.mode || "SHORT",
    category: item.category || "general",
    video_url: item.video_url || "",
    tg_file_id: item.tg_file_id || "",
    cover_tg_file_id: item.cover_tg_file_id || "",
    cover_url: item.cover_url || "",
    story_tg_file_id: item.story_tg_file_id || "",
    story_url: item.story_url || "",
    slot_utc_ms: slot.slot_utc_ms,
    slot_ist: slot.slot_ist,
    status: "pending",
    queued_at: Date.now(),
  };
  const nextQ = [...queue.filter(x => x && (x.status === "pending" || (Date.now() - Number(x.done_at || 0)) < 7 * 86400000)), entry];
  await writeGhJson(env, SCHED_PUB_PATH, nextQ, qCur.sha, `schedule ${item.id} at ${slot.slot_ist}`);
  const isLong = String(entry.mode).toUpperCase() === "LONG";
  const plats = isLong ? "YouTube + Facebook Page" : "YouTube + Facebook Page + Instagram";
  const pos = pending.length + 1;
  const txt =
    `✅ Smart Auto-Schedule Set! (#${pos} in queue)\n\n` +
    `🎬 ${entry.title}\n` +
    `⏰ Publish Time: ${slot.slot_ist}\n` +
    `📣 Platforms: ${plats}\n\n` +
    `(Roz 3 best slots: 9:00 AM • 1:30 PM • 7:00 PM IST — poora schedule dekhne ke liye /schedule dabaein.)`;
  if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: txt });
  else await tgReply(env.TG_TOKEN, chatId, txt, true);
}

async function showScheduleQueue(env, chatId) {
  const qCur = await readGhJson(env, SCHED_PUB_PATH, []);
  const queue = Array.isArray(qCur.data) ? qCur.data : [];
  const pending = queue.filter(x => x && x.status === "pending").sort((a, b) => Number(a.slot_utc_ms) - Number(b.slot_utc_ms));
  if (!pending.length) {
    await tgReply(env.TG_TOKEN, chatId, "📅 Abhi koi video schedule queue mein nahi hai.\n\nKisi bhi ready video par '📅 Auto-Schedule (3/Day Best IST ⭐)' dabaein — roz 9:00 AM, 1:30 PM aur 7:00 PM IST par apne aap publish hoti jayegi!", true);
    return;
  }
  const lines = [`📅 Scheduled Videos Queue (${pending.length} pending — 3/Day IST):`, ""];
  const kb = [];
  for (let i = 0; i < Math.min(12, pending.length); i++) {
    const it = pending[i];
    const badge = String(it.mode || "SHORT").toUpperCase() === "LONG" ? "📺" : "📱";
    lines.push(`${i + 1}. ${badge} ${it.slot_ist}\n   🎬 ${String(it.title || "").slice(0, 62)}`);
    if (i < 6) kb.push([{ text: `❌ Cancel #${i + 1} (${String(it.slot_ist).slice(0, 18)})`, callback_data: `scancel:${it.id}` }]);
  }
  await tgApi(env, "sendMessage", {
    chat_id: chatId,
    text: lines.join("\n").slice(0, 3900),
    reply_markup: { inline_keyboard: kb },
  });
}

async function handleScheduleCancel(env, cq) {
  const chatId = String(cq.message && cq.message.chat ? cq.message.chat.id : "");
  const msgId = cq.message ? cq.message.message_id : null;
  await tgApi(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) return;
  const targetId = String(cq.data || "").replace("scancel:", "").trim();
  const qCur = await readGhJson(env, SCHED_PUB_PATH, []);
  const queue = Array.isArray(qCur.data) ? qCur.data : [];
  const nextQ = queue.filter(x => !(x && x.id === targetId && x.status === "pending"));
  await writeGhJson(env, SCHED_PUB_PATH, nextQ, qCur.sha, `cancel scheduled ${targetId}`);
  if (msgId) await tgApi(env, "editMessageText", { chat_id: chatId, message_id: msgId, text: "🗑️ Scheduled video queue se hata di gayi. (/schedule se updated list dekhein)" });
}

async function runScheduledPublishes(env) {
  try {
    const qCur = await readGhJson(env, SCHED_PUB_PATH, []);
    const queue = Array.isArray(qCur.data) ? qCur.data : [];
    const nowMs = Date.now();
    const dueIdx = queue.findIndex(x => x && x.status === "pending" && Number(x.slot_utc_ms || 0) <= nowMs + 2 * 60 * 1000);
    if (dueIdx < 0) return;
    const item = queue[dueIdx];
    const isLong = String(item.mode || "SHORT").toUpperCase() === "LONG";
    let ytVideoUrl = item.video_url
      ? (item.tg_file_id ? `${item.video_url}#vg_tg=${item.tg_file_id}` : item.video_url)
      : (item.tg_file_id ? `tgfile://${item.tg_file_id}` : "");
    if (item.cover_tg_file_id) ytVideoUrl += `#vg_th_tg=${item.cover_tg_file_id}`;
    if (item.cover_url) ytVideoUrl += `#vg_th_url=${encodeURIComponent(item.cover_url)}`;

    const ytTask = dispatchGH(env, "publish_video.yml", {
      video_url: ytVideoUrl, title: item.title, description: item.description,
      tags: item.tags, mode: item.mode, category: item.category, privacy: "scheduled",
    });
    const fbTask = publishFacebookPage(env, item);
    const igTask = !isLong ? publishInstagramReelAndStory(env, item) : Promise.resolve({ ok: true, msg: "ℹ️ Long video: IG skip" });
    const [ytOk, fbRes, igRes] = await Promise.all([ytTask, fbTask, igTask]);

    queue[dueIdx] = { ...item, status: "done", done_at: Date.now() };
    await writeGhJson(env, SCHED_PUB_PATH, queue, qCur.sha, `published scheduled ${item.id}`);

    const chatId = String(env.ALLOWED_CHAT_ID || env.TG_CHAT_ID || "").trim();
    if (chatId) {
      const msg =
        `⏰ Scheduled Auto-Publish Triggered!\n` +
        `🎬 ${item.title}\n` +
        `🗓️ Slot: ${item.slot_ist}\n` +
        `▶️ YouTube: ${ytOk ? "25m Auto-Public shuru ✓" : "fail"}\n` +
        `${fbRes ? fbRes.msg : ""}\n` +
        `${igRes ? igRes.msg : ""}`.trim();
      await tgReply(env.TG_TOKEN, chatId, msg, true);
    }
  } catch (e) {
    console.log("runScheduledPublishes err:", e);
  }
}
