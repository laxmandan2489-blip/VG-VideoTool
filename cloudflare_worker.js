// Cloudflare Worker: Full Telegram Control for Cloud VideoTool (100% Free, 24/7)
// Supports:
//   - Sending Hindi/Hinglish script -> renders video on GitHub Cloud & returns to Telegram + Drive
//   - Sending a .zip file with caption "update" -> auto-updates your GitHub Cloud repo!
//   - Sending "/purana" -> rolls back the last cloud update!
//   - Sending "/status" -> checks cloud bridge status

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("VideoTool Cloud Bridge is LIVE!", { status: 200 });
    }
    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("ok", { status: 200 });
    }
    const msg = update.message || update.edited_message;
    if (!msg) return new Response("ok", { status: 200 });

    const chatId = String(msg.chat.id);
    if (env.ALLOWED_CHAT_ID && chatId !== String(env.ALLOWED_CHAT_ID).trim()) {
      return new Response("ok", { status: 200 });
    }

    // 1) Handle Telegram ZIP update (caption: update)
    const doc = msg.document;
    const cap = (msg.caption || "").trim().toLowerCase();
    if (doc && doc.file_name && doc.file_name.toLowerCase().endsWith(".zip") && cap.includes("update")) {
      const ok = await dispatchGH(env, "apply_update.yml", {
        action: "update",
        file_id: doc.file_id,
      });
      await tgReply(env.TG_TOKEN, chatId, ok
        ? "📦 Update ZIP mil gayi! Cloud par compile aur install kar raha hoon (1 min)..."
        : "❌ GitHub update trigger fail ho gaya. GH_TOKEN permission (Contents + Actions: Read & Write) check karo.");
      return new Response("ok", { status: 200 });
    }

    const text = (msg.text || "").trim();
    if (!text) return new Response("ok", { status: 200 });

    // 2) Handle /start, /status, /purana
    if (text === "/start" || text === "/status") {
      await tgReply(env.TG_TOKEN, chatId,
        "☁️ VideoTool Cloud Online hai!\n• Script bhejo -> video bankar aayegi\n• ZIP + caption `update` -> cloud update\n• `/purana` -> pichhla version wapas");
      return new Response("ok", { status: 200 });
    }

    if (text.toLowerCase() === "/purana") {
      const ok = await dispatchGH(env, "apply_update.yml", {
        action: "rollback",
        file_id: "",
      });
      await tgReply(env.TG_TOKEN, chatId, ok
        ? "⏪ Pichhla version (/purana) cloud par restore kar raha hoon (30 sec)..."
        : "❌ Rollback trigger fail ho gaya.");
      return new Response("ok", { status: 200 });
    }

    if (text.length < 15) {
      await tgReply(env.TG_TOKEN, chatId, "⚠️ Script bahut chhoti hai. Poori script bhejo!");
      return new Response("ok", { status: 200 });
    }

    // 3) Render video from script
    const isLong = text.toUpperCase().startsWith("LONG");
    const mode = isLong ? "LONG" : "SHORT";
    const ok = await dispatchGH(env, "make_video.yml", { script: text, mode: mode });
    await tgReply(env.TG_TOKEN, chatId, ok
      ? `🚀 Script mil gayi (${mode})! Cloud par video banana shuru kar diya hai.\n5–10 min me Telegram aur Google Drive par aa jayegi.`
      : "❌ GitHub render trigger fail ho gaya. GH_TOKEN aur GH_REPO check karo.");
    return new Response("ok", { status: 200 });
  },
};

async function dispatchGH(env, workflowFile, inputs) {
  const res = await fetch(
    `https://api.github.com/repos/${env.GH_REPO}/actions/workflows/${workflowFile}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GH_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "VideoTool-Cloud-Worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main", inputs }),
    }
  );
  return res.ok;
}

async function tgReply(token, chatId, text) {
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}
