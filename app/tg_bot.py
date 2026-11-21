"""v2.8: Telegram bot – phone se script/topic bhejo, laptop video banata hai, video wapas phone pe.

   6_TELEGRAM_BOT chalao (window khuli rehne do). api keys.txt me:  TELEGRAM=123456:ABC...
   Pehla insaan jo bot ko /start bhejta hai wahi malik ban jaata hai – baaki sab ignore.
"""
import sys, os, re, time, json, threading, subprocess, datetime, queue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
import requests
from common import log, read_keys as _read_keys_disk, no_console_freeze, TOOL, OUT, WORK, LOG_FILE

_KC = {"t": 0, "k": {}}


def read_keys():
    """v2.18: keys 2 min yaad rakho (har message pe folder khangalna dheema tha)."""
    if time.time() - _KC["t"] > 120 or not _KC["k"]:
        _KC["k"] = _read_keys_disk(); _KC["t"] = time.time()
    return _KC["k"]

OWNER_FILE = TOOL / "telegram_owner.txt"
JOBS = TOOL / "temp" / "bot_jobs"
TG_LIMIT = 49 * 1024 * 1024            # bot 50 MB tak bhej sakta hai

HELP = ("🎬 VG Video Bot\n\n"
        "📝 Script bhejo (har line nayi line pe) – video bana ke bhej dunga.\n"
        "💡 Ya sirf topic:  TOPIC: mangal ki dhool kitni khatarnak hai\n\n"
        "🎤 Apni awaaz: voice note / mp3 bhejo, phir script bhejo ya 'bana do' likho.\n"
        "🤳 Apna bolta hua video bhejo – main chehra + footage wali video banaunga.\n"
        "🎬 Apni footage: clips bhejo (saath me likho kahan lagani hai), phir script bhejo.\n"
        "☁️ Badi file (20 MB+): Drive ke 'VG Footage' folder me daalo aur likho:\n"
        "     'drive wali footage' / 'drive wali awaaz' / 'drive wali video se shorts'\n\n"
        "🤝 /prompt + script (agli lines me) – ChatGPT/Claude/Gemini APP ke liye prompt. App ka JSON jawab\n"
        "     yahan paste karo, phir wahi script bhejo -> visual + editing aapke AI ke plan se (API nahi chahiye)\n"
        "🧰 Visual galat? /badlo 3  likho phir sahi clip/photo bhejo (ya /badlo 3 https://youtu.be/.. 45)\n"
        "     -> sirf line 3 badal ke nayi video. /badlo = shot list. Laptop pe: output\\..._EDIT_KIT (CapCut)\n\n"
        "✏️ Video pasand nahi aayi? Bas likho kya galat hai, jaise:\n"
        "     'footage kharab hai sahi karo' / 'line 5 ki clip badlo' / 'captions bade karo'\n\n"
        "🗣️ /awaaz_demo – ek line 10 deep awaazon me sunao\n"
        "     /awaaz_demo आपकी अपनी लाइन   (apni line pe demo)\n"
        "     /awaaz Orus  – wahi awaaz set karo\n\n"
        "🎞️ Lambi video: script ki pehli line me  LONG  likho (sections ke upar ## naam)\n"
        "     ya pehle likho 'agli video long'. Short ke liye kuch mat likho.\n\n"
        "⚙️ Setting hamesha ke liye: likho  'setting: captions bade aur peele karo'\n"
        "     /settings – abhi ki settings   /wapas_setting – pichhla badlaav ulta\n"
        "     Caption style: kisi video ka screenshot bhejo, caption me likho 'caption style'\n"
        "✨ Pro effects (line me likho): [map: Chamoli, Uttarakhand]  [label: 1:14 PM]\n"
        "     [news: headline | NASA]  [gola]  [bubble: sawaal]  [list: a, b, c]  [ink]\n"
        "🧠 SEEKHO: koi bhi reel/video bhejo, caption: seekho  -> bot editing style + sound effects seekhega\n"
        "     caption 'sound nikalo' = sirf sound.  /style = kya seekha  /style_bhool  /hatao 2 5  /sounds\n"
        "🎨 Apne effects: file bhejo, caption me likho: layer / transition / motion subscribe /\n"
        "     sound boom (ya whoosh, riser, ding, pop...) / music\n"
        "🔄 Tool update: Claude wali ZIP file bot ko bhejo (caption: update).  /purana – pichhla version\n"
        "🧹 /safai – purani files hatao   🩺 /health – sab theek hai?\n\n"
        "/log – log ki aakhri lines\n/rok – chal rahi video rok do\n"
        "/wapas – pichhli video wapas\n/naya – bheji hui footage/awaaz bhool jaao\n"
        "/status – abhi kya ban raha hai\n/shorts – lambi_video folder se Shorts\n/help – ye message")


# v2.16c: "/" menu + neeche buttons
COMMANDS = [
    ("kaam", "✅ Mera kaam – aapko kya karna baaki hai (keys, sounds, review)"),
    ("prompt", "🤝 ChatGPT/Claude/Gemini app ke liye visual+editing prompt (script saath me)"),
    ("badlo", "🧰 Pichhli video ki ek line ka visual badlo – /badlo 3 phir clip bhejo"),
    ("key", "API key lagao – jaise /key PEXELS abc123 (message khud mit jaayega)"),
    ("aaj", "📝 ChatGPT/Gemini script prompt (topic aap do) + aaj ka target"),
    ("guide", "📖 Roz ka kaam kaise karna hai"),
    ("help", "Saari madad – kya kya kar sakta hoon"),
    ("status", "Abhi kya ban raha hai"),
    ("style", "Bot ne reels se kya seekha"),
    ("sounds", "Mere sound effects ki ginti"),
    ("hatao", "Ghatiya sound hatao – jaise /hatao 2 5"),
    ("transitions", "Transitions ki list (kaunsi lagti hai)"),
    ("effects", "3D / motion effects ki list"),
    ("effect_hatao", "Koi motion effect band karo – jaise /effect_hatao whip_in"),
    ("transition_hatao", "Ghatiya transition hatao – jaise /transition_hatao 3"),
    ("awaaz_demo", "10 deep awaazein suno"),
    ("awaaz", "Awaaz chuno – jaise /awaaz Orus"),
    ("settings", "Abhi ki settings dekho"),
    ("wapas_setting", "Pichhla setting badlaav ulta karo"),
    ("wapas", "Pichhli video wapas bhejo"),
    ("shorts", "lambi_video folder se Shorts banao"),
    ("naya", "Bheji hui footage/awaaz bhool jao"),
    ("rok", "Chalti video roko"),
    ("log", "Log ki aakhri lines (galti ho to Claude ko bhejo)"),
    ("health", "Sab theek hai? jaanch"),
    ("safai", "Purani files hata ke jagah banao"),
    ("style_bhool", "Seekha hua style bhool jao"),
    ("purana", "Pichhla version wapas lagao"),
    ("backup", "Abhi Google Drive me poora backup banao"),
    ("backup_status", "Aakhri backup kab bana"),
    ("seekho_folder", "seekho_videos folder ki saari reels se seekho (20MB limit nahi)"),
    ("mode", "Abhi kaunsa mode hai (safe mode jaanch)"),
]
BTN = {"video": "🎬 Video banao", "seekho": "🧠 Seekho", "status": "📊 Status", "settings": "⚙️ Settings",
       "sounds": "🔊 Sounds", "madad": "❓ Madad", "aaj": "▶️ Aaj shuru karo", "guide": "📖 Guide",
       "kaam": "✅ Mera kaam"}
MAIN_KB = {"keyboard": [[{"text": BTN["aaj"]}, {"text": BTN["kaam"]}],
                        [{"text": BTN["video"]}, {"text": BTN["seekho"]}],
                        [{"text": BTN["status"]}, {"text": BTN["settings"]}],
                        [{"text": BTN["sounds"]}, {"text": BTN["guide"]}, {"text": BTN["madad"]}]],
           "resize_keyboard": True, "is_persistent": True,
           "input_field_placeholder": "Script / TOPIC: likho, ya button dabao"}
VIDEO_HOWTO = ("🎬 Video banane ke 2 tareeke:\n\n"
               "1️⃣ Apni script bhejo – har line nayi line pe, aakhri line 'follow kar lo'.\n"
               "   Line ke peeche  || english shabd  = us line pe kya dikhe\n\n"
               "2️⃣ Sirf topic bhejo:\n   TOPIC: समुद्र की सबसे गहरी जगह\n\n"
               "✨ Pro effects line me: [map: Chamoli, Uttarakhand]  [label: 1:14 PM]  [news: headline | NASA]\n"
               "   [gola]  [bubble: sawaal]  [list: a, b, c]  [ink]  [boom]\n\n"
               "Example:\n"
               "30 अक्टूबर को एक हेलीकॉप्टर रडार से गायब हो गया [boom] || helicopter flying\n"
               "ये चमोली के पहाड़ों के ऊपर था [map: Chamoli, Uttarakhand] || mountains\n"
               "ऐसे ही तगड़े फैक्ट्स के लिए फॉलो कर लो || subscribe button\n\n"
               "Lambi video: pehli line me  LONG  likho.")
SEEKHO_HOWTO = ("🧠 Bot ko editing sikhao:\n\n"
                "• Koi bhi reel / video bhejo, caption me likho:  seekho\n"
                "   → editing ka andaaz + sound effects dono seekhega\n"
                "• Sirf sound chahiye:  caption  sound nikalo\n"
                "• /style – kya seekha   /style_bhool – bhool jao   /hatao 2 5 – ghatiya sound hatao\n\n"
                "(20 MB se chhoti video bhejna)")


def batch_note(tg, chat, kind):
    """v2.18: 5 script wala batch – har video ka nateeja gino, aakhir me report."""
    try:
        import daily
        if kind in ("done", "gate", "fail"): daily.mark(kind)
        b = SESSION.get("batch")
        if not b: return
        b[kind] = b.get(kind, 0) + 1; b["left"] -= 1
        if b["left"] <= 0:
            d = daily.load_plan(); tgt = daily.target()
            tg.send(chat, f"📋 REPORT: {b['n']} scripts me se\n✅ {b.get('done', 0)} video bani\n"
                          f"⛔ {b.get('gate', 0)} quality gate pe ruki\n🎙️ {b.get('awaaz', 0)} awaaz ki wajah se ruki\n"
                          f"❌ {b.get('fail', 0)} galti\n\n🎯 Aaj ka target: {d.get('done', 0)}/{tgt}")
            SESSION.pop("batch", None)
    except Exception as e:
        log(f"  batch note: {e}", show=False)


def video_kb(lambi=False):
    rows = [[{"text": "🔁 Footage sahi karo", "callback_data": "v:footage"},
             {"text": "🖼️ Naya thumbnail", "callback_data": "v:thumb"}],
            [{"text": "✏️ Kuch aur badlo", "callback_data": "v:edit"}]]
    if lambi:
        rows[1].append({"text": "✂️ Shorts banao", "callback_data": "v:shorts"})
    return {"inline_keyboard": rows}



def visual_summary(video):
    """v3.4: har line pe kya laga – aam bhasha me. QC sirf tab bole jab sach me dikkat ho."""
    video = Path(video)
    out = []
    try:
        q = json.loads(video.with_name(video.stem + "_QC.json").read_text(encoding="utf-8"))
        if not q.get("ok"):
            out.append("⚠️ Video check: " + "; ".join(q.get("problems", []))[:300])
    except Exception:
        pass
    try:
        sc = json.loads(video.with_name(video.stem + "_SCENE_VERIFICATION_REPORT.json").read_text(encoding="utf-8"))
        v = json.loads(video.with_name(video.stem + "_VISUAL_RELEVANCE_REPORT.json").read_text(encoding="utf-8"))
        main = (v.get("identity_lock") or {}).get("main_subject") or ""
        body = [s for s in sc if s.get("status") != "cta"]
        clip = photo = card = other = 0
        for s in body:
            srcs = " ".join(str(a.get("src", "")) for a in s.get("assets") or [])
            if "youtube clip" in srcs: clip += 1
            elif main and main.lower() in srcs.lower(): photo += 1
            elif "card" in srcs or "blender" in srcs or not srcs: card += 1
            else: other += 1
        msg = f"🎯 {len(body)} lines: "
        parts = []
        if clip: parts.append(f"{clip} pe {main or 'subject'} ki asli YouTube clip")
        if photo: parts.append(f"{photo} pe {main or 'subject'} ki photo")
        if other: parts.append(f"{other} pe topic ki footage")
        if card: parts.append(f"{card} pe text card (footage nahi mili)")
        out.append(msg + ", ".join(parts))
        bad = [str(s["line"]) for s in body if s.get("status") in ("wrong_subject", "unrelated", "misleading")]
        if bad: out.append("⚠️ In lines ka visual galat lag raha: " + ", ".join(bad))
    except Exception:
        pass
    return "\n".join(out) or "🎯 Visual report nahi mili"

class TG:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.s = requests.Session()                        # v2.18: ek hi connection – jawab jaldi

    def call(self, method, files=None, _t=60, **params):
        try:
            r = self.s.post(self.base + method, data=params if files else None, json=None if files else params,
                            files=files, timeout=_t)
            j = r.json()
            if not j.get("ok") and "not modified" not in str(j.get("description", "")):
                log(f"  telegram {method}: {str(j)[:200]}", show=False)
            return j.get("result")
        except Exception as e:
            log(f"  telegram {method} error: {e}", show=False)
            return None

    def send(self, chat, text):
        out = None
        for i in range(0, max(1, len(text)), 4000):                 # 4096 limit
            out = self.call("sendMessage", chat_id=chat, text=text[i:i + 4000] or "-")
        return out

    def send_kb(self, chat, text, kb=None):
        return self.call("sendMessage", chat_id=chat, text=text[:4000], reply_markup=kb or MAIN_KB)

    def edit(self, chat, mid, text):
        return self.call("editMessageText", chat_id=chat, message_id=mid, text=text[:4000])

    def send_file(self, chat, path, kind="document", caption=""):
        method = {"video": "sendVideo", "photo": "sendPhoto", "audio": "sendAudio"}.get(kind, "sendDocument")
        with open(path, "rb") as f:
            return self.call(method, files={kind: (Path(path).name, f)}, _t=600,
                             chat_id=str(chat), caption=caption[:1000],
                             **({"supports_streaming": "true"} if kind == "video" else {}))


def keep_awake(on=True):
    """Bot chalu ho tab tak laptop sleep me na jaaye (screen band ho sakti hai)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception:
        pass


def owner():
    try:
        return int(OWNER_FILE.read_text().strip())
    except Exception:
        return None


def python_cmd(script):
    return [sys.executable, str(Path(__file__).parent / script)]


PROGRESS = [
    (re.compile(r"^0\) Gemini script"), "✍️ Gemini script likh raha hai..."),
    (re.compile(r"^2\) "), "🎙️ Awaaz ban rahi hai..."),
    (re.compile(r"^3\) "), "🔎 Har line ki footage dhoondh raha hoon..."),
    (re.compile(r"visuals: (\d+)/(\d+) lines"), "🔎 Footage: {0}/{1} lines"),
    (re.compile(r"Gemini busy hai, (\d+) sec me dobara try \(round (\d+)\)"), "⏳ Google ka Gemini busy hai, {0} sec me dobara try (round {1})..."),
    (re.compile(r"Gemini busy hai \((\w+)\), (\d+) sec baad dobara try \((\d+)/(\d+)\)"),
     "⏳ Gemini busy hai ({0}) – {1} sec baad dobara try ({2}/{3}). Na mila to bina Gemini aage."),
    (re.compile(r"Gemini mil gaya"), "✅ Gemini mil gaya, aage badh raha hoon..."),
    (re.compile(r"awaaz: section (\d+)/(\d+)"), "🎙️ Awaaz: section {0}/{1}"),
    (re.compile(r"LAMBI VIDEO mode"), "🎞️ Lambi video mode ✓"),
    (re.compile(r"^4\) "), "✂️ Editing ho rahi hai..."),
    (re.compile(r"^1\) Video ki editing naap"), "📏 Video ki editing naap raha hoon..."),
    (re.compile(r"^2\) Gemini video dekh"), "👀 Gemini video dekh raha hai..."),
    (re.compile(r"^3\) Sound effects"), "🔊 Sound effects nikaal raha hoon..."),
    (re.compile(r"Demucs"), "🎚️ Bolne wali awaaz alag kar raha hoon (pehli baar install – thoda time)..."),
    (re.compile(r"Final video: (\d+)%"), "🎬 Final video: {0}%"),
    (re.compile(r"^7\) "), "🖼️ Thumbnail, title, description..."),
    (re.compile(r"^8\) Check bot"), "🧐 Check bot video dekh raha hai..."),
    (re.compile(r"footage badal ke dobara"), "🔁 Kuch lines theek kar raha hoon, dobara ban rahi hai..."),
    # v3.5: "footage 9/10 pe atki" – asal me aage ka kaam chal raha tha, bot batata nahi tha
    (re.compile(r"visual jaanch: har scene"), "🎯 Footage mil gayi – ab har scene ki jaanch (galat ho to badlunga)..."),
    (re.compile(r"🔁 line (\d+): behtar visual dhoondh"), "🔁 Line {0} ki footage galat thi – nayi dhoondh raha hoon..."),
    (re.compile(r"🎯 visual relevance: (\d+)%"), "🎯 Footage jaanch poori: {0}% sahi"),
    (re.compile(r"(\d+)/(\d+) scenes ✓"), "✂️ Editing: {0}/{1} scenes"),
    (re.compile(r"^5\) Captions"), "🔤 Captions, music, sound laga raha hoon..."),
    (re.compile(r"YouTube clips ka time poora"), "🎞 YouTube clips ka time poora – baaki lines pe photo/stock"),
]


STATUS_FILE = TOOL / "bot_status.json"


def status_load():
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def status_save(d):
    try:
        STATUS_FILE.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass


def restart_bot(why, chat):
    """Bot band karo – 6_TELEGRAM_BOT wali loop 10 sec me naye code ke saath chalu karti hai."""
    st = status_load(); st["restart"] = {"why": why, "chat": chat, "t": time.time()}; status_save(st)
    def _bye():
        time.sleep(2); os._exit(3)
    threading.Thread(target=_bye, daemon=True).start()


def log_tail(n=15):
    try:
        return "\n".join(LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])[-3500:]
    except Exception:
        return "(log nahi mila)"


class Worker(threading.Thread):
    def __init__(self, tg):
        super().__init__(daemon=True)
        self.tg = tg; self.q = queue.Queue(); self.current = None; self.proc = None; self.stopped = False
        self._last_fmt = "short"

    def add(self, chat, kind, data=None):
        self.q.put((chat, kind, data or {}))
        return self.q.qsize() + (1 if self.current else 0)

    def run(self):
        while True:
            chat, kind, data = self.q.get()
            self.current = {"video": "video", "feedback": "sudhaar", "shorts": "shorts",
                            "transcribe": "awaaz sun raha hoon", "seekho": "video se seekh raha hoon"}.get(kind, kind)
            try:
                if kind == "video":
                    self.make_video(chat, data)
                elif kind == "feedback":
                    self.feedback(chat, data)
                elif kind == "shorts":
                    self.make_shorts(chat, data.get("video"))
                elif kind == "transcribe":
                    self.transcribe(chat, data)
                elif kind == "demo":
                    self.demo(chat, data)
                elif kind == "seekho":
                    self.seekho(chat, data)
                elif kind == "thumb":
                    self.new_thumb(chat, data)
                elif kind == "badlo":
                    self.badlo(chat, data)
            except Exception as e:
                self.tg.send(chat, f"❌ Gadbad: {e}")
            self.current = None

    def badlo(self, chat, data):
        """v3.16: Edit Kit se ek line / shot ka visual badal ke nayi final video."""
        import edit_kit
        kit = Path(data["kit"])
        if data.get("url"):
            man = json.loads((kit / "kit.json").read_text(encoding="utf-8"))
            li = int(data["line"]) - 1
            dur = sum(s_["dur"] for s_ in man["shots"] if s_["line"] == li) or 4.0
            self.tg.send(chat, f"⬇️ YouTube se {dur:.1f} sec ka hissa le raha hoon...")
            try:
                edit_kit.youtube_part(data["url"], data.get("ss", 0), dur, kit / "BADLO" / f"line_{li+1}.mp4")
            except Exception as e:
                return self.tg.send(chat, f"❌ YouTube clip nahi kati: {str(e)[:200]}")
        self.tg.send(chat, "🧰 Visual badal ke nayi video bana raha hoon (1-4 minute)...")
        try:
            new = edit_kit.rebuild(kit)
        except Exception as e:
            return self.tg.send(chat, f"❌ Nayi video nahi bani: {str(e)[:300]}")
        if not new:
            return self.tg.send(chat, "BADLO me koi file nahi mili.")
        try:
            if Path(new).stat().st_size < 49 * 1024 * 1024:
                self.tg.send_file(chat, new, "video", caption="✅ Visual badal diya – captions/awaaz wahi")
            else:
                self.tg.send(chat, f"✅ Nayi video bani (50 MB se badi, laptop pe): {new}")
        except Exception as e:
            self.tg.send(chat, f"✅ Nayi video bani: {new}\n(bhejne me dikkat: {e})")

    def _run(self, cmd, env, chat, title):
        """v2.11: kaam chalao + har 2-3 min 'chal raha hai' + 10 min kuch na badle to alarm. /rok se band."""
        msg = self.tg.send(chat, f"⏳ {title}\nShuru ho gaya...")
        mid = (msg or {}).get("message_id")
        status = "Shuru ho gaya..."; last_edit = 0; t0 = time.time(); last_line = time.time(); alarmed = False
        p = subprocess.Popen(cmd, cwd=str(TOOL), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                             creationflags=0x4000 if os.name == "nt" else 0)   # v2.18: BELOW_NORMAL – bot/laptop tez rahe
        self.proc = p
        lines_q = queue.Queue()

        def reader():
            for ln in p.stdout:
                lines_q.put(ln)
            lines_q.put(None)
        threading.Thread(target=reader, daemon=True).start()
        while True:
            try:
                line = lines_q.get(timeout=5)
            except queue.Empty:
                line = ""
            if line is None:
                break
            line = line.strip()
            if line:
                last_line = time.time(); alarmed = False
                for rx, tpl in PROGRESS:
                    m = rx.search(line)
                    if m:
                        status = tpl.format(*m.groups()); break
            mins = int((time.time() - t0) // 60)
            quiet = time.time() - last_line
            if mid and (time.time() - last_edit > (8 if line else 150)):    # line aayi: 8s; chup: har 2.5 min
                beat = f"\n🕐 {mins} min se chal raha hai" if mins >= 2 else ""
                self.tg.edit(chat, mid, f"⏳ {title}\n{status}{beat}"); last_edit = time.time()
            if quiet > 600 and not alarmed:
                alarmed = True
                self.tg.send(chat, "⚠️ 10 minute se kuch nahi badla. Ho sakta hai atak gaya ho.\n"
                                   "Rukna hai to /rok bhejo. Log ki aakhri lines:\n\n" + log_tail(12))
        p.wait()
        self.proc = None
        return p.returncode

    def _fail(self, chat):
        batch_note(self.tg, chat, "fail")
        self.tg.send(chat, "❌ Video nahi ban payi. log.txt ki aakhri lines (Claude ko bhej do):\n\n" + log_tail(15))

    def deliver(self, chat, video, upload=None, thumbs=(), drive=None, minutes=None):
        video = Path(video)
        # v3.1: "✅ ban gayi" tabhi jab file sach me pahunch jaaye. Pehle sirf "bhej raha hoon".
        head = f"📤 Video tayyar hai, bhej raha hoon..." + (f" ({minutes} min lage)" if minutes else "")
        self.tg.send(chat, head)
        try:                                               # v3.4: ek seedha, saaf message (pehle 2 confusing message)
            self.tg.send(chat, visual_summary(video))
        except Exception:
            pass
        for t in thumbs:
            if Path(t).exists() and "short" in Path(t).name:
                self.tg.send_file(chat, t, "photo", "🖼️ Thumbnail")
        if upload and Path(upload).exists():
            self.tg.send(chat, "📝 Copy karke YouTube pe daalo:\n\n" + Path(upload).read_text(encoding="utf-8"))
        size = video.stat().st_size if video.exists() else 0
        sent = None
        if 0 < size <= TG_LIMIT:
            sent = self.tg.send_file(chat, video, "video", "🎬 " + video.stem[:80])
            if not sent:                                     # video ki tarah nahi gayi to file ki tarah
                sent = self.tg.send_file(chat, video, "document", "🎬 " + video.stem[:80])
        if not sent:
            where = f"Google Drive → {Path(drive).parent.name} → {Path(drive).name}" if drive else \
                f"laptop ke output folder me ({video.name})"
            why = "Ye badi hai isliye Telegram pe nahi aa sakti." if size > TG_LIMIT else "Telegram pe nahi bhej paaya."
            self.tg.send(chat, f"📁 {why}\nAapko yahan mil jaayegi: {where}")
        else:
            self.tg.send(chat, "✅ Video Telegram pe pahunch gayi!")
            if drive:
                self.tg.send(chat, f"☁️ Drive me bhi hai: {Path(drive).parent.name} → {Path(drive).name}")
        try:                                                   # v2.16c: neeche buttons
            self.tg.send_kb(chat, "Kuch badalna hai? Button dabao 👇 (ya seedha likh do kya badalna hai)",
                            video_kb(lambi="lambi" in str(video).lower() or self._last_fmt == "lambi"))
        except Exception:
            pass

    def _env(self, res, **kw):
        env = dict(os.environ, VG_BOT="1", VG_RESULT=str(res), PYTHONIOENCODING="utf-8")
        for k, v in kw.items():
            if v: env[k] = str(v)
        return env

    def _after(self, chat, res, extra=""):
        r = json.loads(res.read_text(encoding="utf-8"))
        self._last_fmt = r.get("format", "short")
        if extra or r.get("note"):
            n = extra or r.get("note")
            self.tg.send(chat, n if n.startswith("⚠️") else "✏️ " + n)
        self.deliver(chat, r["video"], r.get("upload"), r.get("thumbs", []), r.get("drive"), r.get("minutes"))
        rv = r.get("review") or {}
        if rv.get("score") is not None:                # v3.6: video ke BAAD poori jaanch ka saar
            iss = sorted(rv.get("issues") or [], key=lambda x: -x[2])[:4]
            txt = f"🧐 Video Review: {rv['score']}/100 ({rv.get('verdict', '')})"
            txt += "\n" + "\n".join(f"• {m}" for _, m, _ in iss) if iss else "\n✅ captions, visual, timing – koi dikkat nahi mili"
            if rv.get("not_done"): txt += "\n(check nahi hua: " + "; ".join(rv["not_done"][:2]) + ")"
            if r.get("timing"): txt += "\n" + r["timing"]
            try: self.tg.send(chat, txt)
            except Exception: pass
        HIST.add(res)
        try:
            import daily
            daily.add_topic(Path(r["script"]).read_text(encoding="utf-8"))
        except Exception:
            pass
        batch_note(self.tg, chat, "done")

    def make_video(self, chat, d):
        JOBS.mkdir(parents=True, exist_ok=True)
        jid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sp = JOBS / f"script_{jid}.txt"; res = JOBS / f"result_{jid}.json"
        sp.write_text(d["text"].strip() + "\n", encoding="utf-8")
        st = {"voice": "meri"} if d.get("voice") and not d.get("face") else {}
        env = self._env(res, VG_SCRIPT=sp, VG_FOOTAGE=d.get("footage"), VG_NOTES=d.get("notes"),
                        VG_VOICE=d.get("voice"), VG_FACE=d.get("voice") if d.get("face") else None,
                        VG_STYLE_JSON=json.dumps(st) if st else None)
        if d.get("no_gemini"): env["VG_NO_GEMINI_WAIT"] = "1"
        if d.get("allow_ms"): env["VG_ALLOW_MS"] = "1"
        if d.get("avoid"):
            av = JOBS / f"avoid_{jid}.txt"; av.write_text("\n".join(d["avoid"]), encoding="utf-8"); env["VG_AVOID"] = str(av)
        first = [l for l in d["text"].strip().splitlines() if l.strip().upper() not in ("LONG", "SHORT")][0][:60]
        rc = self._run(python_cmd("make_video.py"), env, chat, f"Video: {first}")
        if rc == 42:                                   # Gemini bahut busy – aapse poochho
            SESSION["retry"] = d
            kb = {"inline_keyboard": [[{"text": "▶️ Abhi bana do (bina Gemini check)", "callback_data": "g:now"}],
                                      [{"text": "⏰ 15 minute baad dobara try karo", "callback_data": "g:later"}]]}
            self.tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                         text="⚠️ Google ka Gemini abhi bahut busy hai, footage check nahi ho pa raha.\n"
                              "Bina check ke footage thodi kam sahi ho sakti hai. Kya karun?")
            return
        if rc == 43:                                   # v2.17c: Gemini awaaz nahi – chupchaap awaaz nahi badli
            try: why = json.loads(res.read_text(encoding="utf-8")).get("why", "")
            except Exception: why = "Gemini ki awaaz nahi mili."
            SESSION["retry"] = d
            kb = {"inline_keyboard": [[{"text": "⏰ 30 min baad apne-aap try", "callback_data": "a:later"}],
                                      [{"text": "🎙️ Microsoft awaaz se hi bana do", "callback_data": "a:ms"}],
                                      [{"text": "❌ Rehne do", "callback_data": "a:no"}]]}
            self.tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                         text=f"🎙️ Video nahi banayi – {why}\nAapki chuni hui awaaz ke bina video kharab lagti hai. Kya karun?")
            batch_note(self.tg, chat, "awaaz")
            return
        if rc == 44 and res.exists():                  # v3.5: quality gate fail – PEHLE video bhejo, phir note
            try: r_ = json.loads(res.read_text(encoding="utf-8"))
            except Exception: r_ = {}
            why = "\n".join("• " + w for w in (r_.get("gate") or {}).get("why", [])[:6]) or "• quality kam"
            self.stopped = False
            self._after(chat, res)                     # v3.5 FIX: video ab rukti nahi (user: "mera video ruk gaya")
            SESSION["retry"] = d; SESSION["gate_res"] = str(res)    # retry pe purani clips avoid
            kb = {"inline_keyboard": [[{"text": "🔁 Nayi footage ke saath dobara banao", "callback_data": "q:retry"}]]}
            self.tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                         text="⚠️ Video upar bhej di. Jaanch me ye kamzori dikhi:\n" + why +
                              "\n\nPasand na aaye to dobara bana deta hoon.")
            batch_note(self.tg, chat, "gate")
            return
        if (rc != 0 or not res.exists()) and not self.stopped and not d.get("safe"):
            # v3.39: preserve crash log before SAFE MODE overwrites log.txt
            try:
                _lf = TOOL / "log.txt"
                if _lf.exists():
                    _tail = "\n".join(_lf.read_text(encoding="utf-8", errors="ignore").splitlines()[-30:])
                    (TOOL / "last_crash.txt").write_text(_tail, encoding="utf-8")
            except Exception:
                pass
            # v2.14: bot khud sambhale – ek baar seedhe "safe mode" me dobara
            self.tg.send(chat, "⚠️ Ek galti aayi (last_crash.txt me save). Safe mode me dobara bana raha hoon...")
            env["VG_SAFE"] = "1"; d = dict(d, safe=True)
            rc = self._run(python_cmd("make_video.py"), env, chat, f"Video (safe mode): {first}")
            if rc == 0 and res.exists():
                self.tg.send(chat, "✅ Safe mode me ban gayi (Gemini check / kuch effects ke bina). "
                                   "Pasand na aaye to bas likho kya badalna hai.")
        self.stopped = False
        if rc != 0 or not res.exists():
            return self._fail(chat)
        self._after(chat, res)
        try:
            r = json.loads(res.read_text(encoding="utf-8"))
            from common import read_style
            if r.get("format") == "lambi" and read_style(TOOL / "style.txt").get("lambi_se_shorts", "haan") == "haan":
                self.tg.send(chat, "✂️ Ab isi lambi video se Shorts bhi kaat raha hoon...")
                self.q.put((chat, "shorts", {"video": r["video"]}))
        except Exception:
            pass

    def feedback(self, chat, d):
        prev = Path(d["prev"]); pr = json.loads(prev.read_text(encoding="utf-8"))
        jid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        res = JOBS / f"result_{jid}.json"
        sp = JOBS / f"script_{jid}.txt"
        sp.write_text(Path(pr["script"]).read_text(encoding="utf-8"), encoding="utf-8")   # purani script ki copy
        env = self._env(res, VG_SCRIPT=sp, VG_PREV=prev, VG_FEEDBACK=d["text"])
        for k, v in (pr.get("env") or {}).items():
            env.setdefault(k, v)
        rc = self._run(python_cmd("make_video.py"), env, chat, "Sudhaar: " + d["text"][:50])
        if rc != 0 or not res.exists():
            return self._fail(chat)
        self._after(chat, res)

    def demo(self, chat, d):
        import voice
        keys = read_keys()
        if not keys.get("GEMINI"):
            return self.tg.send(chat, "Gemini key nahi mili – demo nahi ban sakta.")
        JOBS.mkdir(parents=True, exist_ok=True)
        names = d.get("names") or voice.DEEP_MALE
        line = d.get("line") or "मंगल ग्रह की धूल इंसानों के लिए इतनी खतरनाक क्यों है? जवाब सुनकर हैरान रह जाओगे।"
        self.tg.send(chat, f"🗣️ {len(names)} awaazon ka demo bana raha hoon (2-4 minute)...")
        ids = demo_ids()
        for n, ogg in voice.gemini_demo(keys["GEMINI"], line, names, JOBS):
            with open(ogg, "rb") as f:
                r = self.tg.call("sendVoice", files={"voice": f}, _t=120, chat_id=chat, caption=f"🗣️ {n}  →  /awaaz {n}")
            try:
                ids[r["voice"]["file_unique_id"]] = n          # v2.11b: ye voice note wapas aaye to = awaaz chuni
            except Exception:
                pass
        DEMO_FILE.write_text(json.dumps(ids), encoding="utf-8")
        self.tg.send(chat, "Jo pasand aaye uske neeche wala  /awaaz NAAM  dabao (ya likho).")

    def new_thumb(self, chat, d):
        """v2.16c: pichhli video ka naya thumbnail (doosra frame / doosra design)."""
        r = json.loads(Path(d["prev"]).read_text(encoding="utf-8"))
        import meta, random as _r
        from common import read_style
        style = read_style(TOOL / "style.txt")
        video = Path(r["video"]); base = video.with_suffix("")
        srcs = []
        for its in (r.get("items") or {}).values():
            for it in its:
                if it.get("src") == "news card" or not Path(it.get("path", "")).exists(): continue
                srcs.append((it["path"], it.get("kind", "video")))
        _r.shuffle(srcs)                                     # is baar alag frames
        work = WORK / f"thumb_{datetime.datetime.now():%H%M%S}"; (work / "fonts").mkdir(parents=True, exist_ok=True)
        try:
            from common import copy_font, ASSETS
            copy_font(ASSETS / "fonts" / "VTBaloo.ttf", work / "fonts" / "VTBaloo.ttf")
        except Exception:
            pass
        try:
            first = Path(r["script"]).read_text(encoding="utf-8").splitlines()
            first = [l for l in first if l.strip() and not l.startswith("#") and not l.upper().startswith("TITLE:")]
            md = meta.make_meta(read_keys().get("GEMINI"), first[:6] or ["Fact"], None, style)
        except Exception:
            md = {"thumb_text": video.stem[:20]}
        self.tg.send(chat, "🖼️ Naya thumbnail bana raha hoon (1-2 min)...")
        outs = meta.make_thumbs(video, md.get("thumb_text") or "Fact", f"{base}_v{_r.randint(2, 99)}", work,
                                srcs=srcs, key=read_keys().get("GEMINI"), topic=" ".join(first[:1]) if first else "",
                                style=style)
        sent = 0
        for o in outs:
            if "short" in o.name:
                self.tg.send_file(chat, o, "photo", "🖼️ Naya thumbnail"); sent += 1
        if not sent:
            self.tg.send(chat, "❌ Thumbnail nahi ban paya. /log dekho.")

    def seekho(self, chat, d):
        """v2.16: reel se editing style + sound effects seekho."""
        out = JOBS / f"seekho_{datetime.datetime.now():%H%M%S}.json"
        JOBS.mkdir(parents=True, exist_ok=True)
        rc = self._run(python_cmd("seekho.py") + [d["path"], str(out), d.get("mode", "dono")],
                       dict(os.environ, VG_BOT="1", PYTHONIOENCODING="utf-8"), chat, "Video se seekh raha hoon")
        try:
            r = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            r = {"ok": False}
        if rc != 0 or not r.get("ok"):
            return self._fail(chat)
        msg = []
        if "measure" in r:
            m = r["measure"]
            msg.append("🧠 Seekh liya! (" + r.get("how", "") + ")")
            if r.get("summary"): msg.append(r["summary"])
            msg.append(f"✂️ cut har {m.get('shot_sec')} sec • ⚡ flash {m.get('flash_per_min', '-')}/min • "
                       f"🔊 sound {m.get('sfx_per_min', '-')}/min")
            if r.get("tips"): msg.append("📝 " + "\n📝 ".join(r["tips"][:5]))
            if r.get("learned"):
                msg.append(f"\n➡️ Ab aapki videos me ({r.get('note','')}):\n" +
                           "\n".join(f"• {k} = {v}" for k, v in list(r["learned"].items())[:12]))
            if r.get("new_effects"):
                msg.append("\n🆕 Ye effects tool me abhi NAHI hain (ye message Claude ko bhejo, wo jod dega):\n" +
                           "\n".join(f"• {e.get('name')}: {e.get('how','')}" for e in r["new_effects"][:8]))
        if "sounds" in r:
            sn = r.get("sounds") or []
            if sn:
                msg.append(f"\n🔊 {len(sn)} sound effects nikaal ke rakh diye (agli videos me lagenge):\n" +
                           "\n".join(f"{x['n']}. {x['type']} ({x['dur']}s)" for x in sn) +
                           "\nGhatiya lage to likho:  /hatao 2 5")
            else:
                msg.append("\n🔊 Is video se saaf sound effect nahi nikle (shayad lagaataar koi bol raha hai).")
        self.tg.send(chat, "\n".join(msg)[:4000])
        if r.get("preview") and Path(r["preview"]).exists():
            self.tg.send_file(chat, r["preview"], "audio", "🔊 Nikle hue sound – isi kram me (1, 2, 3...)")
        for dm in r.get("demos") or []:                          # v2.17: naya effect seekha – demo + ✅/❌
            if not Path(dm["video"]).exists(): continue
            self.tg.send_file(chat, dm["video"], "video", f"🆕 Naya effect: {dm['name']}\n{dm.get('about','')}")
            kb = {"inline_keyboard": [[{"text": "✅ Rakho", "callback_data": f"r:ok:{dm['name']}"},
                                       {"text": "❌ Hatao", "callback_data": f"r:no:{dm['name']}"}]]}
            self.tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                         text=f"'{dm['name']}' pasand aaya? Rakhoge to agli videos me sahi jagah khud lagega.")
        try:
            if d.get("keep"):                                    # v2.20: seekho_videos folder wali – hata ke _ho_gaye me
                done = Path(d["path"]).parent / "_ho_gaye"; done.mkdir(exist_ok=True)
                Path(d["path"]).replace(done / Path(d["path"]).name)
            else:
                Path(d["path"]).unlink()
        except Exception: pass

    def transcribe(self, chat, d):
        out = JOBS / f"heard_{datetime.datetime.now():%H%M%S}.txt"
        rc = self._run(python_cmd("transcribe.py") + [d["voice"], str(out)], dict(os.environ, PYTHONIOENCODING="utf-8"),
                       chat, "Aapki awaaz sun raha hoon")
        if rc != 0 or not out.exists():
            return self._fail(chat)
        SESSION["heard"] = out.read_text(encoding="utf-8").strip()
        SESSION["await"] = "confirm"
        self.tg.send(chat, "👂 Maine ye suna:\n\n" + SESSION["heard"] +
                     "\n\n✅ Sahi hai to  haan  bhejo.\n✏️ Galat shabd ho to poora sahi text bhej do (har line nayi line pe).")

    def make_shorts(self, chat, video=None):
        start = time.time()
        env = dict(os.environ, VG_BOT="1", PYTHONIOENCODING="utf-8")
        if video: env["VG_LONG_VIDEO"] = str(video)
        rc = self._run(python_cmd("make_shorts.py"), env, chat, "Lambi video se Shorts")
        if rc != 0:
            return self._fail(chat)
        new = sorted([p for p in (OUT / "shorts").glob("*.mp4") if p.stat().st_mtime >= start - 5])
        if not new:
            return self._fail(chat)
        import meta
        from common import read_style
        style = read_style(TOOL / "style.txt")
        drive = None
        for v in new:
            base = str(v.with_suffix(""))
            day = meta.to_drive(v, style)
            self.deliver(chat, v, base + "_UPLOAD.txt", [base + "_thumbnail_short.jpg"], day)


# ------------------------------------------------------------------ session + history
SESSION = {}


def new_session():
    SESSION.clear()
    retry = SESSION.get("retry")
    SESSION.clear()
    SESSION.update({"footage_dir": None, "footage_n": 0, "notes": [], "voice": None, "face": False,
                    "await": None, "pending": None, "heard": None, "dir": None, "fmt": None, "retry": retry})


new_session()


class History:
    F = JOBS / "history.json"

    def all(self):
        try:
            return [p for p in json.loads(self.F.read_text(encoding="utf-8")) if Path(p).exists()]
        except Exception:
            return []

    def add(self, res):
        h = [p for p in self.all() if p != str(res)] + [str(res)]
        JOBS.mkdir(parents=True, exist_ok=True)
        self.F.write_text(json.dumps(h[-20:]), encoding="utf-8")

    def last(self):
        h = self.all(); return h[-1] if h else None


HIST = History()


def sdir():
    if not SESSION.get("dir"):
        d = JOBS / f"session_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        (d / "footage").mkdir(parents=True, exist_ok=True)
        SESSION["dir"] = str(d)
    return Path(SESSION["dir"])


YES = ("haan", "han", "ha", "yes", "ok", "okay", "sahi", "theek", "thik", "👍", "done", "bana do")
GO = ("bana do", "banado", "video banao", "video bana", "shuru", "start karo", "bnao", "bana de")
FOOT_W = ("footage", "clip", "b-roll", "broll", "fotage")
VOICE_W = ("awaaz", "awaj", "aawaz", "voice", "recording", "meri awaaz")
FACE_W = ("chehra", "chehre", "face", "mera video", "bolta")
SHORT_W = ("short", "shorts")
SEEKHO_W = ("seekho", "seekh", "sikho", "sikh lo", "seekh lo", "learn", "style seekho", "sound nikalo", "sounds nikalo",
            "sound nikal", "effects nikalo", "editing seekho")
VEXT = (".mp4", ".mov", ".mkv", ".webm", ".3gp", ".m4v", ".avi")
AEXT = (".mp3", ".m4a", ".wav", ".ogg", ".oga", ".opus", ".aac", ".flac", ".amr")


DEMO_FILE = JOBS / "demo_ids.json"


def demo_ids():
    try:
        return json.loads(DEMO_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_voice(tg, chat, name):
    import voice
    if name.lower() not in voice.GEMINI_VOICES:
        return False
    set_style("gemini_awaaz", name.lower()); set_style("voice", "gemini")
    if SESSION.get("voice") and not SESSION.get("face"):
        SESSION["voice"] = None                                  # galti se li hui recording hatao
    tg.send(chat, f"✅ Ab se awaaz: {voice.GEMINI_VOICES[name.lower()]}\nAb apni script bhejo.")
    return True


def demo_choice(m):
    """Demo wala voice note forward/reply/wapas bheja? -> awaaz ka naam (warna None)."""
    import re as _re
    obj = m.get("voice") or m.get("audio") or {}
    n = demo_ids().get(obj.get("file_unique_id", ""))
    if n: return n
    for src in (m.get("reply_to_message") or {}, m):
        cap = src.get("caption") or ""
        mm = _re.search(r"/awaaz\s+(\w+)", cap)
        if mm and (src is not m or m.get("forward_origin") or m.get("forward_from")):
            return mm.group(1)
    return None


def set_style(key, value):
    """style.txt me ek setting badlo (comment waise hi rehta hai)."""
    import re as _re
    p = TOOL / "style.txt"
    txt = p.read_text(encoding="utf-8")
    pat = _re.compile(rf"^({_re.escape(key)}\s*=\s*)(\S+)", _re.M)
    if pat.search(txt):
        txt = pat.sub(lambda m: m.group(1) + value, txt, count=1)
    else:
        txt += f"\n{key} = {value}\n"
    p.write_text(txt, encoding="utf-8")
    try:                                     # v2.16: aapne khud badli – seekha hua style isko nahi chhuega
        import seekho; seekho.lock_keys([key])
    except Exception:
        pass


def has(t, words):
    t = t.lower(); return any(w in t for w in words)


def drive_footage():
    import meta
    from common import read_style
    root = meta.find_drive(read_style(TOOL / "style.txt"))
    if not root: return None
    d = root / "VG Footage"; d.mkdir(parents=True, exist_ok=True)
    return d


def download(tg, token, file_id, name):
    info = tg.call("getFile", file_id=file_id)
    if not info or not info.get("file_path"):
        return None
    url = f"https://api.telegram.org/file/bot{token}/{info['file_path']}"
    dst = sdir() / name
    with requests.get(url, stream=True, timeout=300) as r:
        if r.status_code != 200: return None
        with open(dst, "wb") as f:
            for ch in r.iter_content(1 << 16): f.write(ch)
    return dst


def ask_kind(tg, chat):
    kb = {"inline_keyboard": [[{"text": "🤳 Mera bolta video (chehra + awaaz)", "callback_data": "k:face"}],
                              [{"text": "🎤 Sirf meri awaaz", "callback_data": "k:voice"}],
                              [{"text": "🎬 Footage (clip)", "callback_data": "k:footage"}],
                              [{"text": "✂️ Lambi video – Shorts banao", "callback_data": "k:shorts"}],
                              [{"text": "🧠 Isse SEEKHO (editing + sound) – video nahi banegi", "callback_data": "k:seekho"}],
                              [{"text": "❌ Kuch mat karo", "callback_data": "k:cancel"}]]}
    tg.call("sendMessage", chat_id=chat, text="Ye video kis kaam ki hai?", reply_markup=kb)


def apply_kind(tg, w, chat, kind, path, caption=""):
    path = Path(path)
    if kind == "footage":
        dst = sdir() / "footage" / path.name
        path.replace(dst); SESSION["footage_dir"] = str(sdir() / "footage"); SESSION["footage_n"] += 1
        if caption: SESSION["notes"].append(f"{dst.name}: {caption}")
        tg.send(chat, f"🎬 Footage mili ({SESSION['footage_n']} clips). Aur bhejo, ya ab script bhejo "
                      "(ya awaaz bhej ke 'bana do').")
    elif kind in ("voice", "face"):
        SESSION["voice"] = str(path); SESSION["face"] = kind == "face"
        did = SESSION.pop("await_self", None)
        if did and did in DRAFTS:                           # v2.20: self video ki script pehle aa chuki thi
            tg.send(chat, ("🤳 Aapka video mila." if kind == "face" else "🎤 Awaaz mili.") + " ✓")
            return show_plan(tg, chat, did)
        tg.send(chat, ("🤳 Aapka video mila." if kind == "face" else "🎤 Awaaz mili.") +
                " Ab script bhejo (captions usi spelling me aayenge), ya 'bana do' likho – main sunke likh dunga.")
    elif kind == "seekho":                                  # v2.20: LEARNING MODE – kabhi video nahi banata
        n = w.add(chat, "seekho", {"path": str(path), "mode": "dono"})
        tg.send(chat, "🧠 Learning mode: is video se editing + sound seekh raha hoon. Koi video NAHI banegi."
                + (f" (line me #{n})" if n > 1 else ""))
    elif kind == "shorts":
        n = w.add(chat, "shorts", {"video": str(path)})
        tg.send(chat, f"✂️ Lambi video mili – Shorts bana raha hoon" + (f" (line me #{n})" if n > 1 else "..."))


def start_video_quiet(w, text):
    """v2.18: batch ki script – bina alag message ke line me."""
    if SESSION.get("fmt") and text.strip().splitlines()[0].strip().upper() not in ("LONG", "SHORT"):
        text = SESSION["fmt"] + "\n" + text
    w.add(owner(), "video", {"text": text})


def start_video(tg, w, chat, text):
    if SESSION.get("fmt") and text.strip().splitlines()[0].strip().upper() not in ("LONG", "SHORT"):
        text = SESSION["fmt"] + "\n" + text
    d = {"text": text, "footage": SESSION.get("footage_dir"), "notes": "\n".join(SESSION.get("notes") or []),
         "voice": SESSION.get("voice"), "face": SESSION.get("face")}
    n = w.add(chat, "video", d)
    extra = []
    if d["footage"]: extra.append(f"{SESSION['footage_n']} aapki clips")
    if d["voice"]: extra.append("aapka chehra" if d["face"] else "aapki awaaz")
    tg.send(chat, "👍 Script mil gayi ✓" + (f" (+ {', '.join(extra)})" if extra else "") +
            (f"  – line me #{n}" if n > 1 else ", video ban rahi hai..."))
    new_session()


# ------------------------------------------------------------------ v2.20: SAFE PRODUCTION – pehle poochho, phir banao
DRAFTS = {}                       # sirf memory me – bot restart = sab draft khatam (purani script kabhi apne-aap nahi)
OFFICE_DIR = JOBS / "office_scripts"
SEEKHO_DIR = TOOL / "seekho_videos"
PROJECTS = {"short": "📱 The Viral Gyaan – SHORT (9:16)", "long": "🎞️ The Viral Gyaan – LAMBI video (16:9)",
            "self": "🤳 Self video (aapki awaaz / chehra)", "office": "🏢 Office video (Grocer)"}


def _did():
    return f"{int(time.time() * 1000) % 100000000}"


def ask_project(tg, chat, texts):
    """Script aate hi: kuch mat banao – pehle poochho kya banana hai."""
    for k in [k for k, v in DRAFTS.items() if time.time() - v["t"] > 6 * 3600]:
        DRAFTS.pop(k, None)
    did = _did()
    DRAFTS[did] = {"texts": texts, "t": time.time(), "proj": None}
    first = next((l.strip() for l in texts[0].splitlines() if l.strip() and l.strip().upper() not in ("LONG", "SHORT")), "")
    pre = SESSION.get("fmt")
    kb = {"inline_keyboard": [[{"text": PROJECTS["short"] + (" ⭐" if pre == "SHORT" else ""), "callback_data": f"p:short:{did}"}],
                              [{"text": PROJECTS["long"] + (" ⭐" if pre == "LONG" else ""), "callback_data": f"p:long:{did}"}],
                              [{"text": PROJECTS["self"], "callback_data": f"p:self:{did}"}],
                              [{"text": PROJECTS["office"] + " – baad me", "callback_data": f"p:office:{did}"}],
                              [{"text": "❌ Kuch mat banao", "callback_data": f"p:no:{did}"}]]}
    tg.call("sendMessage", chat_id=chat, reply_markup=kb,
            text=f"📝 Script mili ✓  ({len(texts)} script" + ("s" if len(texts) > 1 else "") + ")\n"
                 f"Pehli line: {first[:70]}\n\nIska kya banana hai? 👇\n"
                 "(Jab tak aap button nahi dabaoge, KUCH NAHI banega.)")


def _lines(txt):
    return [l for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")
            and l.strip().upper() not in ("LONG", "SHORT")]


def show_plan(tg, chat, did):
    d = DRAFTS.get(did)
    if not d: return tg.send(chat, "Ye script ab yaad nahi (bot restart hua?). Script dobara bhejo.")
    from common import read_style
    st = read_style(TOOL / "style.txt")
    proj = d["proj"]; fmt = "LONG" if proj == "long" else "SHORT"
    n = [len(_lines(x)) for x in d["texts"]]
    sec = sum(n) * (6 if fmt == "LONG" else 4)
    voice = ("aapki recording" + (" + chehra" if SESSION.get("face") else "")) if SESSION.get("voice") \
        else f"AI awaaz ({st.get('gemini_awaaz', 'fixed')})"
    foot = (f"aapki {SESSION.get('footage_n')} clips + " if SESSION.get("footage_dir") else "") + \
        "free stock (Pixabay, Pexels, NASA, Wikimedia) – AI aankh se line se milayi"
    plan = (f"📋 PRODUCTION PLAN\n\nProject: {PROJECTS[proj]}\n"
            f"Format: {'16:9 lambi' if fmt == 'LONG' else '9:16 short'}\n"
            f"Scripts: {len(n)}  •  lines: {', '.join(map(str, n))}  •  andaazan {sec // 60} min {sec % 60} sec\n"
            f"Awaaz: {voice}\nVisuals: {foot}\n"
            f"Captions: {st.get('caption_size', '-')} / {st.get('caption_rang', '-')}  •  Transitions + SFX: haan "
            f"(ek hi transition baar-baar nahi)  •  Music: haan (awaaz ke neeche dabi)\n"
            "YouTube pe apne-aap upload: ❌ NAHI\n\nShuru karoon?")
    kb = {"inline_keyboard": [[{"text": "▶️ Haan, banao", "callback_data": f"s:go:{did}"}],
                              [{"text": "❌ Cancel", "callback_data": f"s:no:{did}"}]]}
    tg.call("sendMessage", chat_id=chat, text=plan, reply_markup=kb)


def project_choice(tg, w, chat, data):
    parts = data.split(":")
    if len(parts) < 3: return
    what, did = parts[1], parts[2]
    d = DRAFTS.get(did)
    if not d:
        return tg.send(chat, "⌛ Ye purana button hai – wo script ab yaad nahi. Kuch nahi banaya. Script dobara bhejo.")
    if data.startswith("p:"):
        if what == "no":
            DRAFTS.pop(did, None); return tg.send(chat, "👍 Theek hai, kuch nahi banaya.")
        if what == "office":
            OFFICE_DIR.mkdir(parents=True, exist_ok=True)
            f = OFFICE_DIR / f"office_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
            f.write_text("\n\n===\n\n".join(d["texts"]), encoding="utf-8"); DRAFTS.pop(did, None)
            return tg.send(chat, "🏢 Office video mode abhi taiyar NAHI hai – script save kar li (bot_jobs\\office_scripts).\n"
                                 "Ye mode banane ke liye: 2-3 Canva sample videos + raw footage chahiye (Claude ko dena).")
        d["proj"] = what
        if what == "self" and not SESSION.get("voice"):
            SESSION["await_self"] = did
            return tg.send(chat, "🤳 Self video: ab apni recording bhejo – awaaz (voice note) ya chehre wala video.\n"
                                 "Caption me likho: awaaz  (ya)  face\nAate hi plan dikhaunga – usse pehle kuch nahi banega.")
        return show_plan(tg, chat, did)
    if data.startswith("s:"):
        if what != "go":
            DRAFTS.pop(did, None); return tg.send(chat, "👍 Cancel. Kuch nahi banaya.")
        if not d.get("proj"): return show_plan(tg, chat, did)
        DRAFTS.pop(did, None)
        fmt = "LONG" if d["proj"] == "long" else "SHORT"
        texts = [x if x.strip().splitlines()[0].strip().upper() in ("LONG", "SHORT") else fmt + "\n" + x
                 for x in d["texts"]]
        if len(texts) > 1:
            SESSION["batch"] = {"n": len(texts), "left": len(texts)}
            for x in texts: w.add(owner(), "video", {"text": x})
            return tg.send(chat, f"✅ {len(texts)} scripts line me – ek-ek karke banengi. Aakhir me report.")
        SESSION["fmt"] = None
        return start_video(tg, w, chat, texts[0])


FIX_W = ("badlo", "badal", "sahi karo", "theek karo", "thik karo", "sudhaar", "sudhar", "hatao", "kam karo", "zyada",
         "bade", "bada", "chhote", "chhota", "galat", "tez", "dheere", "music", "caption", "clip", "footage", "line",
         "awaaz", "fix", "change")
HI_W = ("hi", "hello", "hii", "hey", "ok", "okay", "thanks", "thank you", "shukriya", "dhanyavaad", "accha", "acha",
        "theek hai", "thik hai", "👍", "🙏", "good", "nice", "update")


def handle_text(tg, w, chat, text):
    t = text.strip(); tl = t.lower()
    if tl.startswith(("/start", "/help")) or t == BTN["madad"]:
        return tg.send_kb(chat, HELP)
    if t == BTN["video"]:
        return tg.send_kb(chat, VIDEO_HOWTO)
    if t == BTN.get("kaam") or tl.startswith("/kaam"):        # v3.12: aapko kya karna hai
        import mera_kaam
        return tg.send_kb(chat, mera_kaam.report())
    if tl.startswith("/key"):                                   # v3.12: Telegram se API key lagao
        import mera_kaam
        parts_ = t.split(None, 2)
        if len(parts_) < 3:
            return tg.send(chat, "Aise bhejo:  /key PEXELS aapki_key\nNaam: GEMINI, PIXABAY, PEXELS, GROQ, OPENROUTER, YOUTUBE, SARVAM")
        ok, msg = mera_kaam.set_key(parts_[1], parts_[2])
        return tg.send(chat, ("✅ " if ok else "❌ ") + msg + ("\n(Aapka key wala message maine chat se hata diya – suraksha ke liye)" if ok else ""))
    if t == BTN["guide"] or tl.startswith("/guide"):
        import daily
        return tg.send_kb(chat, daily.GUIDE)
    _want_long_prompt = tl in ("/aaj long", "/prompt_long", "long prompt", "lambi prompt", "लॉन्ग प्रॉम्प्ट", "लम्बी प्रॉम्प्ट")
    _want_short_prompt = (t == BTN["aaj"] or tl.startswith("/aaj")
                          or tl in ("prompt", "5 prompt", "shorts prompt", "प्रॉम्प्ट", "स्क्रिप्ट प्रॉम्प्ट"))
    if _want_long_prompt:
        import daily
        tg.send_kb(chat, "🎬 LONG NEWS + FACT DOCUMENTARY PROMPT (v3.58)\n"
                         "1) Neeche wala prompt poora COPY karo\n"
                         "2) Sabse upar apna topic likho aur ChatGPT / Gemini me paste karo\n"
                         "3) Jawab copy karke yahan bhejo -> 'Lambi (16:9)' chuno!\n"
                         "Isme har line pe '||' Stock + '|| AI:' hints aur '## Chapters' apne-aap aayenge.")
        tg.send(chat, daily.prompt_text(1, long_mode=True))
        return
    if _want_short_prompt:
        import daily
        d = daily.load_plan(); tgt = daily.target()
        left = max(0, tgt - d.get("done", 0))
        tg.send_kb(chat, f"▶️ AAJ KA PLAN ({d['date']})\n🎯 Target: {tgt} video  •  ban chuki: {d.get('done', 0)}"
                         + (f"  •  ⛔ ruki: {d.get('gate', 0)}" if d.get("gate") else "") +
                         "\n\n📝 v3.58 MASTER PROMPT (5 Shorts — Stock + AI Hints):\n"
                         "1) Neeche wala PROMPT poora COPY karo\n"
                         "2) Topic likho (ya AUTO rehne do -> 5 viral topics khud aayenge)\n"
                         "3) ChatGPT ya Gemini me paste karo\n"
                         "4) Poora jawab copy karke yahan EK message me bhejo -> 5 videos line se banengi!\n"
                         "💡 Long News+Fact documentary prompt ke liye likho:  long prompt")
        tg.send(chat, daily.prompt_text(left or tgt, long_mode=False))
        if not d.get("asked_learn"):
            tg.send(chat, daily.learn_message()); d["asked_learn"] = True; daily.save_plan(d)
        return
    if "===" in t or re.search(r"(?im)^\s*(script|स्क्रिप्ट)\s*\d", t):
        import daily
        parts = daily.split_scripts(t)
        if parts:                                     # v2.20: seedha mat banao – pehle poochho
            return ask_project(tg, chat, parts)
    if t == BTN["seekho"]:
        return tg.send_kb(chat, SEEKHO_HOWTO)
    if t == BTN["status"]: t = tl = "/status"
    elif t == BTN["settings"]: t = tl = "/settings"
    elif t == BTN["sounds"]: t = tl = "/sounds"
    if tl.startswith("/status"):
        return tg.send(chat, f"Abhi: {w.current or 'kuch nahi'}\nLine me: {w.q.qsize()}\n"
                             f"Bheji hui: {SESSION['footage_n']} clips, awaaz: {'haan' if SESSION['voice'] else 'nahi'}")
    import botsys
    if tl.startswith("/purana"):
        if w.current: return tg.send(chat, "Abhi video ban rahi hai – khatam hone ke baad /purana bhejna.")
        ok, msg = botsys.rollback()
        if not ok: return tg.send(chat, "❌ " + msg)
        tg.send(chat, f"⏪ Pichhla version (v{msg}) laga diya. 15 second me wapas aata hoon..."); restart_bot("rollback", chat)
        return
    if tl.startswith("/safai"):
        from common import read_style
        import meta
        st = read_style(TOOL / "style.txt")
        mb = botsys.safai(days=1, keep_videos_days=int(float(st.get("output_rakho_din", "7") or 7)),
                          drive_root=meta.find_drive(st))
        return tg.send(chat, f"🧹 Safai ho gayi – {mb} MB khaali. Laptop me ab {botsys.free_gb():.1f} GB jagah hai.\n"
                             "(Videos sirf wahi hati jo Drive me pahunch chuki thi.)")
    if tl.startswith(("/style_bhool", "/bhool")):
        import seekho
        seekho.forget()
        return tg.send(chat, "🧽 Seekha hua style bhool gaya (backup rakha hai). Ab style.txt wali setting chalegi.")
    if tl.startswith(("/style", "/seekha")):
        import seekho
        return tg.send(chat, seekho.describe()[:4000])
    if tl.startswith("/hatao"):
        import sfx_grab
        nums = [int(x) for x in re.findall(r"\d+", t)]
        gone = sfx_grab.remove(nums)
        return tg.send(chat, (f"🗑️ Hata diye: " + ", ".join(f"{g['n']} ({g['type']})" for g in gone)) if gone
                       else "Ye number nahi mile. Pichhli baar ke sound ki list dekho.")
    if tl.startswith(("/effect_hatao", "/effect_wapas")):
        import recipe
        nm = t.split(maxsplit=1)[1].strip() if len(t.split()) > 1 else ""
        f = recipe.LEARNED / "band.txt"; f.parent.mkdir(parents=True, exist_ok=True)
        cur = set(f.read_text(encoding="utf-8").split()) if f.exists() else set()
        if not nm: return tg.send(chat, "Naam likho, jaise:  /effect_hatao whip_in   (list: /effects)")
        (cur.add if tl.startswith("/effect_hatao") else cur.discard)(nm)
        f.write_text("\n".join(sorted(cur)), encoding="utf-8")
        return tg.send(chat, ("🚫 Band: " if tl.startswith("/effect_hatao") else "✅ Chalu: ") + nm)
    if tl.startswith("/effects"):
        import recipe
        allr = recipe.load_all()
        f = recipe.LEARNED / "band.txt"
        off = sorted(set(f.read_text(encoding="utf-8").split())) if f.exists() else []
        rows = [f"• {k} – {v.get('about','')}" for k, v in allr.items()]
        return tg.send(chat, "🎬 Motion effects (chalu):\n" + ("\n".join(rows) or "koi nahi") +
                       (("\n\n🚫 Band: " + ", ".join(off)) if off else "") +
                       "\n\nBand karna: /effect_hatao naam   Wapas: /effect_wapas naam\n"
                       "Script me zabardasti: line me [fx: card_flip]")
    if tl.startswith("/transition_hatao") or tl.startswith("/transition_wapas"):
        import motion, shutil as _sh
        d = TOOL / "mere_transitions"; hd = d / "_hataye"; hd.mkdir(parents=True, exist_ok=True)
        nums = [int(x) for x in re.findall(r"\d+", t)]
        if tl.startswith("/transition_wapas"):
            back = sorted(p for p in hd.iterdir() if p.is_file())
            done = []
            for k in nums:
                if 1 <= k <= len(back): _sh.move(str(back[k - 1]), str(d / back[k - 1].name)); done.append(back[k - 1].name)
            return tg.send(chat, ("↩️ Wapas: " + ", ".join(done)) if done else "Number galat. /transitions dekho.")
        allf = motion.files("mere_transitions"); done = []
        for k in nums:
            if 1 <= k <= len(allf): _sh.move(str(allf[k - 1]), str(hd / allf[k - 1].name)); done.append(allf[k - 1].name)
        return tg.send(chat, ("🗑️ Hata di (mere_transitions\\_hataye me rakhi): " + ", ".join(done)) if done
                       else "Number galat. /transitions dekho.")
    if tl.startswith("/transitions"):
        import motion
        allf = motion.files("mere_transitions")
        rows = [f"{k}. {'✅' if motion.transition_ok(p) else '🚫 (paper/safed – apne-aap nahi lagti)'} {p.name}"
                for k, p in enumerate(allf, 1)]
        hd = TOOL / "mere_transitions" / "_hataye"
        gone = sorted(p.name for p in hd.iterdir() if p.is_file()) if hd.exists() else []
        return tg.send(chat, ("🎞️ Transitions:\n" + "\n".join(rows) if rows else "Koi transition nahi.") +
                       ("\n\nHataye hue: " + ", ".join(f"{k}. {n}" for k, n in enumerate(gone, 1)) if gone else "") +
                       "\n\nHatane ke liye: /transition_hatao 3   Wapas: /transition_wapas 1")
    if tl.startswith("/backup_status"):
        import botsys
        return tg.send(chat, botsys.backup_status())
    if tl.startswith("/backup"):
        import botsys
        tg.send(chat, "💾 Drive me backup bana raha hoon (1-3 min)...")
        def _b():
            ok, msg = botsys.make_backup(); tg.send(chat, msg if ok else "❌ " + msg)
        threading.Thread(target=_b, daemon=True).start(); return
    if tl.startswith("/sounds"):
        d = TOOL / "mere_sounds"
        rows = [f"• {p.name}: {sum(1 for f in p.iterdir() if f.is_file())} ({sum(1 for f in p.glob('auto_*'))} seekhe)"
                for p in sorted(d.iterdir()) if p.is_dir()] if d.exists() else []
        return tg.send(chat, "🔊 Aapke sound effects:\n" + ("\n".join(rows) or "kuch nahi"))
    if tl.startswith("/health"):
        rep = botsys.health(read_keys())
        return tg.send(chat, "🩺 Jaanch:\n" + "\n".join(("✅ " if ok else "❌ ") + t for ok, t in rep))
    if tl.startswith("/settings"):
        from common import read_style
        st = read_style(TOOL / "style.txt")
        keys_ = ["gemini_awaaz", "caption_size", "caption_rang", "caption_jagah", "caption_shabd", "flash_har_clip",
                 "visual_badle_har", "music_awaaz", "sfx_awaaz", "transition_awaaz", "color_look", "photo_3d",
                 "beat_cut", "loop_ending", "layer", "check_bot", "video_fit", "awaaz_bhaari"]
        return tg.send(chat, "⚙️ Abhi ki settings:\n" + "\n".join(f"{k} = {st.get(k, '-')}" for k in keys_) +
                       "\n\nBadalna ho to likho:  setting: captions chhote karo")
    if tl.startswith("/wapas_setting"):
        return tg.send(chat, "↩️ Pichhla setting badlaav ulta kar diya." if botsys.undo_setting() else "Koi pichhla badlaav nahi mila.")
    if tl.startswith(("setting", "/set", "hamesha", "aage se", "har video me", "change style", "style badlo",
                      "default")):
        body = re.sub(r"^(setting[s]?:?|/set|change style|style badlo)\s*", "", t, flags=re.I)
        if not re.match(r"^\s*[a-z_]+\s*[=:]?\s+\S+\s*$", body.lower()):
            tg.send(chat, "⚙️ Samajh raha hoon...")
        res, samjha = botsys.settings_from_text(read_keys().get("GEMINI"), body)
        if not res:
            return tg.send(chat, "Samajh nahi aaya kya badalna hai. Aise likho: setting: captions bade karo / music kam karo")
        botsys.snapshot()
        for k, v in res.items(): botsys.set_style(k, v)
        return tg.send(chat, "✅ Hamesha ke liye badal diya:\n" + "\n".join(f"• {k} = {v}" for k, v in res.items()) +
                       (f"\n({samjha})" if samjha else "") + "\nUlta karna ho to /wapas_setting")
    # ---------------- v3.1: cinematic engine controls (Telegram se hi)
    if tl.startswith("/cinematic"):
        lvl = (tl.split() + ["medium"])[1]
        presets = {"low": {"transition_gap": "5", "scene_sfx": "nahi", "layer_taakat": "15", "blender_max": "2"},
                   "medium": {"transition_gap": "3.5", "scene_sfx": "haan", "layer_taakat": "30", "blender_max": "4"},
                   "high": {"transition_gap": "2.8", "scene_sfx": "haan", "layer_taakat": "40", "blender_max": "8"}}
        if lvl not in presets:
            return tg.send(chat, "Likho: /cinematic low  |  /cinematic medium  |  /cinematic high")
        botsys.snapshot()
        for k, v in presets[lvl].items(): botsys.set_style(k, v)
        return tg.send(chat, f"🎬 Cinematic intensity = {lvl} ✓ (/wapas_setting se ulta)")
    if tl.startswith("/visual"):
        m = (tl.split() + [""])[1]
        val = {"footage": "nahi", "3d": "haan", "auto": "auto"}.get(m)
        if not val:
            return tg.send(chat, "Likho: /visual auto (footage, na mile to 3D)  |  /visual 3d (science/space pe 3D pehle)  |  /visual footage (3D band)")
        botsys.snapshot(); botsys.set_style("blender3d", val)
        return tg.send(chat, f"🧊 Visual mode = {m} ✓")
    if tl.startswith("/quality"):
        m = (tl.split() + [""])[1]
        val = {"preview": "tez", "final": "achhi"}.get(m)
        if not val:
            return tg.send(chat, "Likho: /quality preview (jaldi, kam quality)  |  /quality final")
        botsys.snapshot(); botsys.set_style("quality", val)
        return tg.send(chat, f"⚙️ Quality = {m} ✓")
    if tl.startswith("/hardware"):
        try:
            import hardware
            r = hardware.detect(write=True); p_ = r["profile"]
            g = ", ".join(f"{x['name']} ({x.get('vram_gb')} GB)" for x in r["gpus"]) or "nahi mila"
            return tg.send(chat, f"💻 {r['cpu']} • RAM {r['ram_gb']} GB • disk {r['disk_free_gb']} GB khaali\nGPU: {g}\n"
                                 f"Blender: {r['blender'].get('version') or 'NAHI'} • FFmpeg: {r['ffmpeg'] or 'NAHI'}\n"
                                 f"FreeVideo local: {'haan' if p_['freevideo_ok'] else 'nahi'} – {p_['freevideo_reason']}")
        except Exception as e:
            return tg.send(chat, f"Hardware check nahi hua: {e}")
    if tl.startswith("/3d_test"):
        tg.send(chat, "🧊 Blender 3D test bana raha hoon (1-4 min)...")
        try:
            from cine import blender_engine as be
            outp = WORK / "blender_test_space.mp4"; WORK.mkdir(parents=True, exist_ok=True)
            r = be.render(outp, 90, 1080, 1920, "space", "orbit", {"accent": [64, 200, 255]}, log=log)
            if r: return tg.send_file(chat, r, "video", "🧊 Blender 3D test (space, orbit camera)")
            return tg.send(chat, "❌ Blender render nahi hua. CHECK_SYSTEM.bat chalao / Blender install karo.")
        except Exception as e:
            return tg.send(chat, f"❌ Blender test error: {e}")
    if tl.startswith("/log"):
        return tg.send(chat, "📜 Log ki aakhri lines:\n\n" + log_tail(20))
    if tl.startswith("/rok"):
        if w.proc and w.proc.poll() is None:
            w.stopped = True
            try:
                w.proc.terminate(); time.sleep(3)
                if w.proc and w.proc.poll() is None: w.proc.kill()
            except Exception:
                pass
            return tg.send(chat, "🛑 Video rok di. Line me agli ho to wo shuru hogi. Dobara banana ho to script phir bhejo.")
        return tg.send(chat, "Abhi koi video nahi ban rahi.")
    if len(t) < 60 and len(t.splitlines()) == 1 and has(tl, ("long", "lambi", "lambi video", "badi video")) \
            and has(tl, ("agli", "next", "banana", "banao", "bana do", "chahiye", "bnani")):
        SESSION["fmt"] = "LONG"
        return tg.send(chat, "🎞️ Theek hai, agli video LAMBI (16:9) banegi. Ab script bhejo (sections ke upar ## naam).")
    if len(t) < 60 and len(t.splitlines()) == 1 and has(tl, ("short",)) and has(tl, ("agli", "next", "banana", "banao", "bana do", "chahiye", "bnani")):
        SESSION["fmt"] = "SHORT"
        return tg.send(chat, "📱 Theek hai, agli video SHORT (9:16) banegi. Ab script bhejo.")
    if tl.startswith("/mode"):
        return tg.send(chat, "🛡️ SAFE MODE chalu:\n• Bot on/restart pe koi purani script / video apne-aap NAHI banti\n"
                             "• Script aaye to pehle poochhta hoon (Short / Lambi / Self / Office) + plan, phir ▶️ dabane pe hi banti hai\n"
                             "• Seekho (learning) se kabhi video nahi banti\n• YouTube pe apne-aap upload nahi\n"
                             f"\nAbhi: {w.current or 'kuch nahi'} • line me: {w.q.qsize()} • rukhi scripts (button ka intezaar): {len(DRAFTS)}")
    if tl.startswith("/seekho_folder"):
        SEEKHO_DIR.mkdir(parents=True, exist_ok=True)
        vids = sorted(p for p in SEEKHO_DIR.iterdir() if p.is_file() and p.suffix.lower() in VEXT)
        if not vids:
            return tg.send(chat, f"📁 Folder khaali hai:\n{SEEKHO_DIR}\nIsme reels daalo (koi size limit nahi), phir /seekho_folder bhejo.")
        for p in vids:
            w.add(chat, "seekho", {"path": str(p), "mode": "dono", "keep": True})
        return tg.send(chat, f"🧠 Learning mode: {len(vids)} videos se ek-ek karke seekhunga (editing + sound). Koi video NAHI banegi.\n"
                             "Seekh li hui videos 'seekho_videos\\_ho_gaye' me chali jayengi.")
    if tl.startswith("/naya"):
        DRAFTS.clear(); SESSION.pop("await_self", None)
        new_session(); return tg.send(chat, "🧹 Theek hai, sab bhool gaya. Naye se shuru karo.")
    if tl.startswith("/wapas"):
        h = HIST.all()
        if len(h) < 2: return tg.send(chat, "Pichhli video nahi hai.")
        r = json.loads(Path(h[-2]).read_text(encoding="utf-8"))
        HIST.add(Path(h[-2]))                       # ab sudhaar isi pe hoga
        tg.send(chat, "⏪ Pichhli video:")
        return w.deliver(chat, r["video"], r.get("upload"), r.get("thumbs", []), r.get("drive"))
    if tl.startswith("/awaaz_demo"):
        line = t[len("/awaaz_demo"):].strip()
        n = w.add(chat, "demo", {"line": line})
        return tg.send(chat, "👂 Demo line me lag gaya" + (f" (#{n})" if n > 1 else "..."))
    if tl.startswith("/awaaz"):
        import voice
        name = t[len("/awaaz"):].strip().split()[0] if t[len("/awaaz"):].strip() else ""
        name = name.split("@")[0]
        if not pick_voice(tg, chat, name):
            return tg.send(chat, "Awaaz ka naam samajh nahi aaya. Ye hain: " + ", ".join(voice.GEMINI_VOICES.values()))
        return
    if tl.startswith("/shorts"):
        n = w.add(chat, "shorts"); return tg.send(chat, f"👍 Shorts line me #{n}")
    if tl.startswith("/prompt"):                       # v3.16: AI APP bridge (bina API)
        import ai_bridge
        body = t.split("\n", 1)[1] if "\n" in t else t[len("/prompt"):]
        lines = ai_bridge.script_lines(body)
        if len(lines) < 2 and DRAFTS:
            lines = ai_bridge.script_lines(list(DRAFTS.values())[-1].get("texts", [""])[0])
        if len(lines) < 2:
            return tg.send(chat, "🤝 Aise bhejo:\n/prompt\nscript ki line 1\nline 2\n...\n\nMain ChatGPT/Claude/Gemini app "
                                 "ke liye prompt dunga. App ka JSON jawab yahan paste karna, phir wahi script bhejna.")
        tg.send(chat, f"🤝 {len(lines)} lines ka prompt neeche hai. Poora COPY karke ChatGPT / Claude / Gemini app me "
                      "paste karo. Wo jo JSON de ({\"vg_plan\"...}) use yahan bhej do. Phir wahi script bhejna.")
        return tg.send(chat, ai_bridge.build_prompt(lines))
    if tl.startswith("/badlo"):                        # v3.16: Edit Kit – ek line ka visual badlo
        import edit_kit
        kit = edit_kit.last_kit()
        if not kit:
            return tg.send(chat, "Abhi koi Edit Kit nahi hai – nayi video (v3.16) banne ke baad /badlo chalega.")
        parts = t.split()
        if len(parts) < 2 or not parts[1].isdigit():
            sl = (kit / "SHOT_LIST.txt")
            txt = sl.read_text(encoding="utf-8-sig")[:3300] if sl.exists() else ""
            return tg.send(chat, f"🧰 Pichhli video: {kit.name[:-9]}\n\n{txt}\n\nLikho: /badlo 3  (phir clip/photo bhejo)\n"
                                 "ya: /badlo 3 https://youtu.be/xxxx 45   (45th second se)")
        ln = int(parts[1])
        url = next((x for x in parts[2:] if x.startswith("http")), None)
        if url:
            ss = next((float(x) for x in parts[2:] if re.match(r"^\d+(\.\d+)?$", x)), 0.0)
            n = w.add(chat, "badlo", {"kit": str(kit), "line": ln, "url": url, "ss": ss})
            return tg.send(chat, f"👍 Line {ln} ka visual YouTube se badal raha hoon" + (f" (line me #{n})" if n > 1 else "..."))
        SESSION["badlo"] = {"line": ln, "kit": str(kit), "t": time.time()}
        return tg.send(chat, f"👍 Ab line {ln} ke liye sahi CLIP ya PHOTO bhejo (10 minute ke andar).")
    if t.startswith("/"):
        return tg.send(chat, HELP)

    if '"vg_plan"' in t or ("aiplan_buf" in SESSION and time.time() - SESSION["aiplan_buf"][1] < 180):
        import ai_bridge                               # v3.16: ChatGPT/Claude/Gemini ka JSON plan paste hua
        prev = SESSION.pop("aiplan_buf", None)
        buf = (prev[0] + "\n" + t) if (prev and time.time() - prev[1] < 180 and '"vg_plan"' not in t) else t
        plan, err = ai_bridge.save(buf)
        if plan:
            return tg.send(chat, f"✅ AI plan save ho gaya: {len(plan['lines'])} lines" +
                           (f", style: {plan['genre']}" if plan.get("genre") else "") +
                           ".\nAb WAHI script bhejo – video isi plan se banegi (3 din tak).")
        if not buf.rstrip().endswith(("}", "```")):
            SESSION["aiplan_buf"] = (buf, time.time())          # Telegram ne lamba paste tod diya – agla hissa jodo
            return tg.send(chat, "⏳ Plan ka agla hissa bhejo (lamba tha, Telegram ne toda)...")
        return tg.send(chat, f"❌ {err}")

    # awaaz ka text confirm
    if SESSION.get("await") == "confirm":
        if tl in YES or (len(t) < 25 and has(tl, YES)):
            return start_video(tg, w, chat, SESSION["heard"])
        if len(t) >= 25:
            return start_video(tg, w, chat, t)

    # Drive wali files
    if "drive" in tl:
        d = drive_footage()
        if not d: return tg.send(chat, "☁️ Google Drive laptop pe nahi mila (Drive for Desktop chalu hai?).")
        files = sorted([p for p in d.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime)
        vids = [p for p in files if p.suffix.lower() in VEXT]; auds = [p for p in files if p.suffix.lower() in AEXT]
        if has(tl, SHORT_W):
            if not vids: return tg.send(chat, "Drive ke 'VG Footage' me koi video nahi mili.")
            n = w.add(chat, "shorts", {"video": str(vids[-1])})
            return tg.send(chat, f"✂️ {vids[-1].name} se Shorts bana raha hoon" + (f" (line me #{n})" if n > 1 else "..."))
        if has(tl, VOICE_W + FACE_W):
            src = (vids[-1] if has(tl, FACE_W) and vids else (auds or vids or [None])[-1])
            if not src: return tg.send(chat, "Drive ke 'VG Footage' me koi recording nahi mili.")
            SESSION["voice"] = str(src); SESSION["face"] = has(tl, FACE_W) and src.suffix.lower() in VEXT
            return tg.send(chat, f"🎤 Drive se li: {src.name}. Ab script bhejo ya 'bana do' likho.")
        if has(tl, FOOT_W):
            fd = sdir() / "footage"
            import shutil
            for p in vids + [p for p in files if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]:
                shutil.copy2(p, fd / p.name); SESSION["footage_n"] += 1
            SESSION["footage_dir"] = str(fd)
            return tg.send(chat, f"🎬 Drive se {SESSION['footage_n']} clips li. Ab script bhejo.")

    is_script = len([l for l in t.splitlines() if l.strip()]) >= 3 or tl.startswith("topic:")
    if is_script:
        return ask_project(tg, chat, [t])               # v2.20: pehle poochho

    if len(t) < 60 and has(tl, SEEKHO_W):              # v2.20: "seekho" likha – kabhi purani video nahi banegi
        p = SESSION.get("pending")
        if p and Path(p).suffix.lower() in VEXT + AEXT and Path(p).exists():
            SESSION.pop("pending", None); SESSION.pop("pending_cap", None)
            n = w.add(chat, "seekho", {"path": p, "mode": "dono"})
            return tg.send(chat, "🧠 Learning mode: pichhli bheji video se seekh raha hoon. Koi video NAHI banegi."
                           + (f" (line me #{n})" if n > 1 else ""))
        return tg.send(chat, SEEKHO_HOWTO + f"\n\n📁 20 MB se badi reels: laptop pe is folder me daalo:\n{SEEKHO_DIR}\nphir /seekho_folder bhejo.")

    if has(tl, GO) and SESSION.get("voice"):
        n = w.add(chat, "transcribe", {"voice": SESSION["voice"]})
        return tg.send(chat, "👂 Pehle aapki awaaz sunke likh raha hoon, phir aapse confirm karunga...")

    if SESSION.get("footage_dir") or SESSION.get("voice"):
        SESSION["notes"].append(t)
        return tg.send(chat, "📝 Note kar liya. Ab script bhejo ya 'bana do' likho.")

    last = HIST.last()
    if tl.strip(" .!") in HI_W:
        return tg.send_kb(chat, "🙂 Main taiyaar hoon. Script bhejo – pehle poochhunga kya banana hai.")
    if last and len(t) < 400 and time.time() - SESSION.get("edit_t", 0) < 900:   # ✏️ dabaya tha – seedha sudhaar
        SESSION.pop("edit_t", None)
        n = w.add(chat, "feedback", {"prev": last, "text": t})
        return tg.send(chat, "🔧 Pichhli video sudhaar raha hoon" + (f" (line me #{n})" if n > 1 else "..."))
    if last and len(t) < 400:                          # v2.20: bina poochhe purani video dobara NAHI banegi
        SESSION["fb"] = {"prev": last, "text": t, "t": time.time()}
        kb = {"inline_keyboard": [[{"text": "🔧 Haan, PICHHLI video me ye sudhaar karo", "callback_data": "f:go"}],
                                  [{"text": "❌ Nahi (kuch mat banao)", "callback_data": "f:no"}]]}
        return tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                       text=f"Kya pichhli video me ye badlaav karna hai?\n“{t[:150]}”\n\n"
                            "(Nayi video ke liye poori script bhejo – kam se kam 3 lines.)")
    return tg.send(chat, "Script kam se kam 3 lines ki bhejo, ya  TOPIC: ...  likho.\n/help dekho.")


def handle_media(tg, w, chat, m, token):
    cap = (m.get("caption") or "").strip()
    obj = None; name = None; kind = None
    if m.get("voice"):
        obj = m["voice"]; name = f"awaaz_{obj['file_unique_id']}.ogg"; kind = "voice"
    elif m.get("audio"):
        obj = m["audio"]; name = obj.get("file_name") or f"audio_{obj['file_unique_id']}.mp3"; kind = "voice"
    elif m.get("video") or m.get("video_note"):
        obj = m.get("video") or m["video_note"]; name = obj.get("file_name") or f"video_{obj['file_unique_id']}.mp4"
    elif m.get("photo"):
        obj = m["photo"][-1]; name = f"photo_{obj['file_unique_id']}.jpg"; kind = "footage"
    elif m.get("document"):
        obj = m["document"]; name = obj.get("file_name") or f"file_{obj['file_unique_id']}"
        ext = Path(name).suffix.lower()
        if ext == ".zip" or (cap or "").lower().startswith("update"):
            kind = "update"
        elif ext in (".txt", ".md"):
            sp = download(tg, token, obj["file_id"], name or "script.txt")
            if not sp:
                return tg.send(chat, "❌ Script file download nahi hui, dobara bhejo.")
            stxt = sp.read_text(encoding="utf-8-sig", errors="replace").strip()
            if not stxt:
                return tg.send(chat, "❌ Ye text file khali hai.")
            tg.send(chat, f"📄 Script file mil gayi ({len(stxt.splitlines())} lines)...")
            return handle_text(tg, w, chat, stxt)
        elif ext in AEXT: kind = "voice"
        elif ext in (".jpg", ".jpeg", ".png", ".webp"): kind = "footage"
        elif ext not in VEXT and kind != "update":
            return tg.send(chat, "Ye file samajh nahi aayi. Video, photo ya awaaz bhejo.")
    if not obj:
        return
    import botsys
    fname = (obj.get("file_name") or "").lower()
    bd = SESSION.get("badlo")
    if bd and time.time() - bd["t"] < 600 and (m.get("video") or m.get("photo") or m.get("document")) and \
            (Path(name or "").suffix.lower() in VEXT + (".jpg", ".jpeg", ".png", ".webp") or m.get("photo") or m.get("video")):
        SESSION.pop("badlo", None)                      # v3.16: /badlo N ke baad aayi clip/photo
        if (obj.get("file_size") or 0) > 20 * 1024 * 1024:
            return tg.send(chat, "📦 20 MB se badi file bot nahi le sakta. Laptop pe Edit Kit ke BADLO folder me daalo "
                                 f"(naam line_{bd['line']}.mp4) aur VISUAL_BADLO.bat chalao.")
        ext = ".jpg" if m.get("photo") else (Path(name or "").suffix.lower() or ".mp4")
        path = download(tg, token, obj["file_id"], f"badlo_{bd['line']}{ext}")
        if not path: return tg.send(chat, "❌ File download nahi hui, dobara bhejo.")
        dst = Path(bd["kit"]) / "BADLO" / f"line_{bd['line']}{ext}"
        import shutil as _sh
        _sh.copy2(path, dst)
        n = w.add(chat, "badlo", {"kit": bd["kit"], "line": bd["line"]})
        return tg.send(chat, f"👍 Line {bd['line']} ke liye mil gayi" + (f" (line me #{n})" if n > 1 else "") + "...")
    if kind == "update" or (m.get("document") and fname.endswith(".zip")):
        if w.current:
            return tg.send(chat, "Abhi video ban rahi hai – khatam hone ke baad ZIP dobara bhejna.")
        tg.send(chat, "🔄 Update file le raha hoon...")
        zp = download(tg, token, obj["file_id"], "update.zip")
        if not zp: return tg.send(chat, "❌ ZIP download nahi hui, dobara bhejo.")
        ok, msg = botsys.update_from_zip(zp)
        if not ok: return tg.send(chat, "❌ " + msg)
        tg.send(chat, f"✅ Update lag gaya ({msg}). Aapki settings bachi hain. 15 second me naye version ke saath wapas aata hoon...")
        restart_bot("update", chat); return
    if has(cap, SEEKHO_W) and (m.get("video") or m.get("audio") or m.get("voice") or m.get("document")):
        if (obj.get("file_size") or 0) > 20 * 1024 * 1024:
            return tg.send(chat, "📦 Telegram bot 20 MB se badi file nahi le sakta.\nLaptop pe ye video is folder me daalo:\n"
                                 f"{SEEKHO_DIR}\nphir yahan /seekho_folder bhejo – wahan koi limit nahi.")
        mode = "sounds" if has(cap, ("sound", "effects nikalo")) and not has(cap, ("seekho", "seekh", "sikho", "learn")) \
            else ("style" if has(cap, ("sirf style", "bina sound")) else "dono")
        tg.send(chat, "⬇️ Video le raha hoon – isse editing" + (" aur sound" if mode == "dono" else "") + " seekhunga...")
        path = download(tg, token, obj["file_id"], name or "seekho.mp4")
        if not path: return tg.send(chat, "❌ File download nahi hui, dobara bhejo.")
        n = w.add(chat, "seekho", {"path": str(path), "mode": mode})
        if n > 1: tg.send(chat, f"Line me #{n} – pehle wala kaam khatam hote hi.")
        return
    if m.get("photo") and has(cap, ("caption style", "caption aise", "captions aise", "caption jaisa", "style copy")):
        tg.send(chat, "🖼️ Screenshot dekh raha hoon...")
        pp = download(tg, token, obj["file_id"], "capstyle.jpg")
        res = botsys.caption_style_from_image(read_keys().get("GEMINI"), pp.read_bytes()) if pp else {}
        if not res: return tg.send(chat, "❌ Caption style samajh nahi aaya (Gemini busy?). Baad me dobara bhejo.")
        botsys.snapshot()
        for k, v in res.items(): botsys.set_style(k, v)
        return tg.send(chat, "✅ Captions ab aise banenge:\n" + "\n".join(f"• {k} = {v}" for k, v in res.items()) +
                       "\nUlta karna ho to /wapas_setting")
    ak = botsys.asset_kind(cap)
    if ak:
        tg.send(chat, "⬇️ Effect le raha hoon...")
        ap = download(tg, token, obj["file_id"], obj.get("file_name") or f"{ak[0]}_{obj['file_unique_id']}" +
                      (".mp4" if m.get("video") else ".ogg" if m.get("voice") else ".mp3" if m.get("audio") else ".png"))
        if not ap: return tg.send(chat, "❌ File download nahi hui.")
        dst = botsys.save_asset(ap, ak[0], ak[1])
        where = {"layer": "layers", "transition": "transitions", "motion": "motion graphics", "music": "music",
                 "sound": f"sound ({ak[1]})"}[ak[0]]
        return tg.send(chat, f"✅ Rakh diya: {where} → {dst.name}\nAgli video se use hoga.")
    dn = demo_choice(m)
    if dn:                                               # demo wala voice note wapas aaya = awaaz chuni
        if pick_voice(tg, chat, dn): return
    if (obj.get("file_size") or 0) > 20 * 1024 * 1024:
        return tg.send(chat, "📦 Ye file 20 MB se badi hai – bot itni badi file nahi le sakta.\n"
                             "Isse Google Drive ke 'VG Footage' folder me daalo, phir likho:\n"
                             "'drive wali footage' / 'drive wali awaaz' / 'drive wali video se shorts'")
    if kind is None:                                  # video: caption se samjho, warna poochho
        if has(cap, SHORT_W): kind = "shorts"
        elif has(cap, FOOT_W): kind = "footage"
        elif has(cap, FACE_W): kind = "face"
        elif has(cap, VOICE_W): kind = "voice"
    tg.send(chat, "⬇️ File le raha hoon...")
    path = download(tg, token, obj["file_id"], name)
    if not path:
        return tg.send(chat, "❌ File download nahi hui, dobara bhejo.")
    if kind is None:
        SESSION["pending"] = str(path); SESSION["pending_cap"] = cap
        return ask_kind(tg, chat)
    if kind == "voice" and not has(cap, VOICE_W):        # v2.11b: pakka karo ki ye aapki recording hai
        SESSION["pending"] = str(path); SESSION["pending_cap"] = cap
        kb = {"inline_keyboard": [[{"text": "🎤 Haan, ye MERI recording hai – video me yahi awaaz", "callback_data": "k:voice"}],
                                  [{"text": "❌ Nahi, galti se bheja", "callback_data": "k:cancel"}]]}
        return tg.call("sendMessage", chat_id=chat, reply_markup=kb,
                       text="Ye awaaz aapki apni recording hai? (AI awaaz chunni ho to /awaaz_demo ke neeche wala neela /awaaz NAAM dabao)")
    apply_kind(tg, w, chat, kind, path, cap if kind == "footage" else "")


_LOCK = {}


def ensure_autostart():
    """v2.18: laptop on -> bot on. Startup shortcut hai? nahi to banao. Task Scheduler (login ke 1 min baad) bhi."""
    if os.name != "nt":
        return
    bat = TOOL / "6_TELEGRAM_BOT.bat"
    try:
        sd = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        lnk = sd / "VG Telegram Bot.lnk"
        if sd.exists() and not lnk.exists():
            ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}'); $s.TargetPath='{bat}'; "
                  f"$s.WorkingDirectory='{TOOL}'; $s.WindowStyle=7; $s.Save()")
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, timeout=30)
            log("  startup shortcut dobara bana diya ✓", show=False)
    except Exception as e:
        log(f"  startup shortcut check: {e}", show=False)
    try:
        q = subprocess.run(["schtasks", "/Query", "/TN", "VG Telegram Bot"], capture_output=True, timeout=20)
        if q.returncode != 0:
            r = subprocess.run(["schtasks", "/Create", "/TN", "VG Telegram Bot", "/SC", "ONLOGON", "/DELAY", "0001:00",
                                "/TR", f'cmd /c start "VG TELEGRAM BOT" /min "{bat}"', "/F"], capture_output=True,
                               timeout=30, text=True, errors="replace")
            log(f"  task scheduler: {'laga ✓' if r.returncode == 0 else 'nahi laga (admin chahiye) – shortcut hi chalega'}",
                show=False)
    except Exception as e:
        log(f"  task scheduler check: {e}", show=False)


def single_instance():
    """v2.17c: sirf EK bot chale. Doosra khula to (25 sec rukke) khud band – aur apni duplicate window bhi."""
    import socket
    for k in range(6):
        try:
            sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sk.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1) \
                if os.name == "nt" else None
            sk.bind(("127.0.0.1", 48731)); sk.listen(1)
            _LOCK["s"] = sk
            return True
        except OSError:
            time.sleep(5)                                  # update ke baad purana band ho raha ho – thoda ruko
    print("\n  ⚠️ Bot pehle se chal raha hai (doosri window me). Ye wali band kar raha hoon.")
    log("  duplicate bot band kiya (ek hi chalega)", show=False)
    try:
        st = status_load(); own = owner()
        if own and time.time() - st.get("dup_msg", 0) > 3600:
            keys = read_keys()
            if keys.get("TELEGRAM"):
                TG(keys["TELEGRAM"]).send(own, "ℹ️ Bot ki ek aur window khul gayi thi – usse band kar diya. Ek hi bot chal raha hai ✓")
                st["dup_msg"] = time.time(); status_save(st)
    except Exception:
        pass
    # v3.16 FIX (log 16 Nov: "duplicate bot band kiya" har 40 sec, 6 ghante tak): pehle parent PID ko taskkill
    # karte the – lekin 'py -3' / venv launcher ki wajah se parent asal me py.exe tha, cmd ki loop nahi. Loop
    # 10 sec baad phir chalati thi -> hamesha ka chakkar. Ab exit code 77: 6_TELEGRAM_BOT.bat ise dekh ke khud band.
    if os.name == "nt":                                    # purani 6_TELEGRAM_BOT.bat (Telegram update use nahi badalta)
        _kill_bat_loop()                                   # 77 nahi samajhti – uski cmd window hi band karo
    os._exit(77)


def _kill_bat_loop():
    """v3.16: is duplicate python ke upar wali cmd.exe (jo 6_TELEGRAM_BOT.bat chala rahi hai) dhoondh ke band karo.
    Sirf wahi cmd jiski command line me 6_TELEGRAM_BOT ho – aapki koi aur window nahi."""
    try:
        pid = os.getppid()
        for _ in range(4):
            ps = (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
                  "if($p){ \"$($p.ParentProcessId)|$($p.Name)|$($p.CommandLine)\" }")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                               timeout=20, errors="replace")
            parts = (r.stdout or "").strip().split("|", 2)
            if len(parts) < 3: return
            ppid, name, cl = parts
            if name.lower() == "cmd.exe" and "6_telegram_bot" in cl.lower():
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
                return
            pid = int(ppid)
    except Exception:
        pass


def main():
    no_console_freeze()
    print("\n" + "=" * 56 + "\n   VG TELEGRAM BOT – chalu hai. Ye window KHULI rehne do.\n" + "=" * 56 + "\n")
    single_instance()
    keys = {}
    for k in range(30):                                   # OneDrive file der se de sakta hai
        keys = _read_keys_disk()
        if keys.get("TELEGRAM"): break
        time.sleep(10)
    token = keys.get("TELEGRAM")
    if not token:
        print("  TELEGRAM key nahi mili. api keys.txt me nayi line:  TELEGRAM=123456789:ABC...")
        time.sleep(60); return
    tg = TG(token)
    me = None
    for k in range(60):                                   # v2.18: laptop on hote hi internet der se aata hai – 10 min ruko
        me = tg.call("getMe", _t=20)
        if me: break
        print(f"  Internet / Telegram ka intezaar... ({k+1}/60)")
        time.sleep(10)
    if not me:
        print("  Telegram se judd nahi paaya. Key sahi hai? Internet chal raha hai?")
        time.sleep(30); return                            # bat loop 10 sec me dobara chalayegi
    ensure_autostart()
    print(f"  Bot: @{me.get('username')}  ✓")
    try:                                                   # v2.16c: "/" likhte hi commands ki list
        tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in COMMANDS])
        tg.call("setChatMenuButton", menu_button={"type": "commands"})
    except Exception as e:
        log(f"  commands menu nahi laga: {e}", show=False)
    own = owner()
    print("  Malik: " + (str(own) if own else "abhi koi nahi – phone se bot ko /start bhejo"))
    keep_awake(True)
    w = Worker(tg); w.start()
    import botsys
    st = status_load()
    if own:
        rs = st.pop("restart", None)
        if rs and rs.get("why") == "update":                 # v2.17c: update ke baad Drive backup
            def _ab():
                time.sleep(60)
                ok, msg = botsys.make_backup()
                if ok: tg.send(own, "💾 Naye version ka backup Drive me rakh diya ✓")
            threading.Thread(target=_ab, daemon=True).start()
        if rs and time.time() - rs.get("t", 0) < 300:
            tg.send_kb(own, f"✅ Wapas aa gaya – ab version v{botsys.version()} chal raha hai.\n"
                            "Naya: neeche buttons 👇 aur '/' likhte hi saare commands." if rs.get("why") != "rollback"
                       else f"✅ Wapas aa gaya – pichhla version v{botsys.version()} chal raha hai.")
        else:
            off = time.time() - st.get("beat", time.time())
            gap = (f" (pichhle {off/3600:.1f} ghante off tha)" if off > 3600 else
                   f" (pichhle {off/60:.0f} minute off tha)" if off > 900 else "")
            tg.send_kb(own, f"🟢 Main on ho gaya!{gap}  v{botsys.version()}\nScript, topic, awaaz ya footage bhejo – "
                            "ya neeche button dabao 👇")
    status_save(st)
    if own:                                           # v3.11: naya version laga -> "kya naya" seedha Telegram pe
        try:
            lv = TOOL / "seekha" / "last_version.txt"
            cur = botsys.version(); old_v = lv.read_text(encoding="utf-8").strip() if lv.exists() else ""
            if cur and cur != old_v:
                nf = TOOL / "app" / "UPDATE_NOTES.txt"
                notes = nf.read_text(encoding="utf-8").strip() if nf.exists() else ""
                tg.send(own, (f"🆕 UPDATE LAGA: v{old_v or '?'} -> v{cur}\n\n" + notes)[:3900])
                lv.parent.mkdir(parents=True, exist_ok=True); lv.write_text(cur, encoding="utf-8")
        except Exception as e:
            log(f"  (update note nahi bheja: {e})", show=False)

    # ---- pin kiya status: har 5 min "🟢 Online HH:MM" (time purana dikhe = bot off)
    def beat():
        while True:
            try:
                own_ = owner()
                d = status_load(); d["beat"] = time.time()
                now = datetime.datetime.now().strftime("%d %b %H:%M")
                txt = f"🟢 Bot ONLINE · {now} pe check kiya\nAbhi: {w.current or 'kuch nahi ban raha'} · line me: {w.q.qsize()}\n" \
                      "(Ye time 10 min se purana dikhe to bot/laptop off hai)"
                if own_:
                    if d.get("pin_id"):
                        r = tg.call("editMessageText", chat_id=own_, message_id=d["pin_id"], text=txt)
                        if r is None and "pin_id" in d: d.pop("pin_id")
                    if not d.get("pin_id"):
                        r = tg.call("sendMessage", chat_id=own_, text=txt, disable_notification=True)
                        if r and r.get("message_id"):
                            d["pin_id"] = r["message_id"]
                            tg.call("pinChatMessage", chat_id=own_, message_id=r["message_id"], disable_notification=True)
                status_save(d)
            except Exception as e:
                log(f"  status pin error: {e}", show=False)
            time.sleep(300)
    threading.Thread(target=beat, daemon=True).start()

    # ---- laptop band / restart pe khabar (Windows thode second deta hai)
    def on_close(*_):
        try:
            own_ = owner(); d = status_load()
            if own_:
                tg.call("sendMessage", _t=5, chat_id=own_, text="🔴 Laptop band/restart ho raha hai – main OFF ho raha hoon.")
                if d.get("pin_id"):
                    tg.call("editMessageText", _t=5, chat_id=own_, message_id=d["pin_id"],
                            text=f"🔴 Bot OFFLINE · {datetime.datetime.now():%d %b %H:%M} se")
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            HANDLER = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            def _h(ev):
                if ev in (2, 5, 6):               # window band / logoff / shutdown
                    on_close(); return False
                return False
            main._ctrl = HANDLER(_h)          # reference rakhna zaroori
            ctypes.windll.kernel32.SetConsoleCtrlHandler(main._ctrl, True)
        except Exception as e:
            log(f"  shutdown handler nahi laga: {e}", show=False)

    # ---- roz ki jaanch + jagah kam ho to safai
    def daily():
        time.sleep(90)                              # shuru me pehle bot ko chalne do
        while True:
            d0 = status_load()
            if time.time() - d0.get("health_t", 0) < 20 * 3600:     # roz ek hi baar
                time.sleep(3600); continue
            d0["health_t"] = time.time(); status_save(d0)
            try:
                rep = botsys.health(read_keys())
                bad = [t for ok, t in rep if not ok]
                if botsys.free_gb() < 5:
                    mb = botsys.safai(days=2)
                    bad.append(f"jagah kam thi – {mb} MB khud saaf kiya")
                if bad and owner():
                    tg.send(owner(), "🩺 Bot ki jaanch me ye mila:\n" + "\n".join("⚠️ " + b for b in bad))
                botsys.safai(days=3)
                try:                                           # v2.18: roz seekhne ke liye reels maango
                    import daily
                    from common import read_style as _rs
                    pl = daily.load_plan()
                    if owner() and not pl.get("asked_learn") and _rs(TOOL / "style.txt").get("seekho_maango", "haan") == "haan":
                        tg.send(owner(), daily.learn_message()); pl["asked_learn"] = True; daily.save_plan(pl)
                except Exception as e:
                    log(f"  learn ask: {e}", show=False)
                ok_b, msg_b = botsys.make_backup()             # v2.17c: roz ek backup
                if not ok_b: log(f"  roz ka backup: {msg_b}", show=False)
            except Exception as e:
                log(f"  daily check error: {e}", show=False)
            time.sleep(3600)
    threading.Thread(target=daily, daemon=True).start()

    # v2.20 STARTUP SAFETY: bot band tha / restart hua – tab ke saare purane messages CHHOD do.
    # (Pehle yahi purani script dobara bana deta tha: Telegram purane messages phir se bhej deta hai.)
    offset = None; skipped = 0
    try:
        for _ in range(30):
            old = tg.call("getUpdates", _t=20, timeout=0, **({"offset": offset} if offset else {}))
            if not old: break
            skipped += len(old); offset = old[-1]["update_id"] + 1
        if offset: tg.call("getUpdates", _t=20, timeout=0, offset=offset)
    except Exception as e:
        log(f"  purane messages saaf nahi hue: {e}", show=False)
    BOOT_T = time.time()
    print(f"  🛡️ Safe start: {skipped} purane message chhode – koi purana kaam nahi chalega")
    if skipped and owner():
        tg.send(owner(), f"🛡️ Bot band/restart ke time ke {skipped} purane message chhod diye – koi purani script ya video "
                         "apne-aap NAHI banegi. Kuch banana ho to abhi dobara bhejo.")
    last_ok = time.time()
    while True:
        ups = tg.call("getUpdates", _t=70, timeout=50, **({"offset": offset} if offset else {}))
        if ups is None:
            if time.time() - last_ok > 120:
                print("  ⚠️ Telegram tak nahi pahunch pa raha (internet band ya network block?)")
            # v3.16: internet band ho to har 5 sec log spam nahi – dheere-dheere 5 -> 60 sec tak intezaar
            time.sleep(min(60, 5 + (time.time() - last_ok) / 10)); continue
        if time.time() - last_ok > 600 and owner():
            tg.send(owner(), f"🟡 Pichhle {(time.time()-last_ok)/60:.0f} minute internet/Telegram nahi mila tha. "
                             "Ab wapas online hoon – beech ke messages ab dekh raha hoon.")
        last_ok = time.time()
        for u in ups:
            offset = u["update_id"] + 1
            try:
                if u.get("callback_query"):
                    cq = u["callback_query"]; chat = cq["message"]["chat"]["id"]
                    tg.call("answerCallbackQuery", callback_query_id=cq["id"])
                    if chat != owner(): continue
                    data = cq.get("data") or ""
                    kind = data.split(":", 1)[-1]
                    if data.startswith(("p:", "s:")):            # v2.20: project / plan buttons
                        project_choice(tg, w, chat, data); continue
                    if data.startswith("f:"):                     # v2.20: sudhaar sirf haan dabane pe
                        fb = SESSION.pop("fb", None)
                        if kind == "go" and fb and time.time() - fb["t"] < 3 * 3600:
                            n = w.add(chat, "feedback", {"prev": fb["prev"], "text": fb["text"]})
                            tg.send(chat, "🔧 Pichhli video sudhaar raha hoon" + (f" (line me #{n})" if n > 1 else "..."))
                        else:
                            tg.send(chat, "👍 Theek hai, kuch nahi banaya.")
                        continue
                    if data.startswith("a:") and SESSION.get("retry"):   # v2.17c: awaaz nahi mili
                        d = dict(SESSION.pop("retry"))
                        if kind == "ms":
                            d["allow_ms"] = True; w.add(chat, "video", d); tg.send(chat, "▶️ Microsoft awaaz se bana raha hoon...")
                        elif kind == "later":
                            threading.Timer(1800, lambda d=d: w.add(chat, "video", d)).start()
                            tg.send(chat, "⏰ Theek hai, 30 minute baad apne-aap dobara try karunga.")
                        else:
                            tg.send(chat, "👍 Theek hai, chhod diya.")
                        continue
                    if data.startswith("q:"):                     # v2.17c: quality gate
                        if kind == "send" and SESSION.get("gate_res"):
                            w._after(chat, Path(SESSION.pop("gate_res"))); SESSION.pop("retry", None)
                        elif kind == "retry" and SESSION.get("retry"):
                            d = dict(SESSION.pop("retry")); gr = SESSION.pop("gate_res", None)
                            try:                                   # pichhli (kharab) clips dobara nahi
                                its = json.loads(Path(gr).read_text(encoding="utf-8")).get("items") or {}
                                d["avoid"] = [x.get("url") for v in its.values() for x in v if x.get("url")]
                            except Exception:
                                pass
                            w.add(chat, "video", d); tg.send(chat, "🔁 Dobara bana raha hoon (nayi footage ke saath)...")
                        continue
                    if data.startswith("r:"):                     # v2.17: seekha hua effect rakho / hatao
                        import seekho
                        _, yn, nm = (data.split(":", 2) + ["", ""])[:3]
                        ok = seekho.approve(nm, yn == "ok")
                        tg.send(chat, ("✅ Rakh liya: " + nm + " – agli videos me lagega." if yn == "ok" else "🗑️ Hata diya: " + nm)
                                if ok else "Ye effect ab nahi mila (pehle hi rakha/hataya?).")
                        continue
                    if data.startswith("v:"):                     # v2.16c: video ke neeche wale buttons
                        last = HIST.last()
                        if not last:
                            tg.send(chat, "Pichhli video nahi mili."); continue
                        if kind == "footage":
                            n = w.add(chat, "feedback", {"prev": last, "text": "footage kharab hai sahi karo"})
                            tg.send(chat, "🔁 Galat footage badal ke dobara bana raha hoon" + (f" (line me #{n})" if n > 1 else "..."))
                        elif kind == "thumb":
                            w.add(chat, "thumb", {"prev": last})
                        elif kind == "shorts":
                            try:
                                v = json.loads(Path(last).read_text(encoding="utf-8"))["video"]
                                w.add(chat, "shorts", {"video": v}); tg.send(chat, "✂️ Shorts kaat raha hoon...")
                            except Exception:
                                tg.send(chat, "Video file nahi mili.")
                        elif kind == "edit":
                            SESSION["edit_t"] = time.time()          # v2.20: agla message = isi video ka sudhaar
                            tg.send(chat, "✏️ Bas likh do kya badalna hai, jaise:\n• line 3 ki clip badlo\n"
                                          "• captions bade karo\n• awaaz thodi tez karo\n• music kam karo\n"
                                          "• line 2 me 'मंगल' ki jagah 'मार्स' likho")
                        continue
                    if data.startswith("g:") and SESSION.get("retry"):
                        d = dict(SESSION.pop("retry"))
                        if kind == "now":
                            d["no_gemini"] = True; w.add(chat, "video", d)
                            tg.send(chat, "▶️ Theek hai, abhi bana raha hoon (bina Gemini check).")
                        else:
                            threading.Timer(900, lambda d=d: w.add(chat, "video", d)).start()
                            tg.send(chat, "⏰ Theek hai, 15 minute baad apne-aap dobara try karunga.")
                        continue
                    if kind == "cancel":
                        SESSION.pop("pending", None); SESSION.pop("pending_cap", None)
                        tg.send(chat, "👍 Theek hai, chhod diya. Kuch nahi banega.")
                        continue
                    if SESSION.get("pending"):
                        p = SESSION.pop("pending"); cap = SESSION.pop("pending_cap", "")
                        apply_kind(tg, w, chat, kind, p, cap)
                    continue
                m = u.get("message") or {}
                chat = (m.get("chat") or {}).get("id")
                if not chat: continue
                if m.get("date", time.time()) < BOOT_T - 30: continue      # v2.20: shuru hone se pehle ka – chhodo
                text = (m.get("text") or "").strip()
                own = owner()
                if own is None and text.startswith("/start"):
                    OWNER_FILE.write_text(str(chat)); own = chat
                    print(f"  Malik set: {chat} ✓")
                if chat != own:
                    tg.send(chat, "Ye private bot hai."); continue
                def _go(m=m, chat=chat, text=text):       # v2.18: har message alag – ek bada kaam baaki ko na roke
                    try:
                        if text:
                            secret = text.lower().startswith("/key")
                            if secret:                    # v3.12: API key wala message chat se mita do + print me nahi
                                try: tg.call("deleteMessage", chat_id=chat, message_id=m.get("message_id"))
                                except Exception: pass
                            print(f"  [{datetime.datetime.now():%H:%M}] message: {'/key ****' if secret else text[:40]}")
                            handle_text(tg, w, chat, text)
                        else:
                            handle_media(tg, w, chat, m, token)
                    except Exception as e:
                        import traceback
                        with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(traceback.format_exc())
                        try: tg.send(chat, f"❌ Gadbad: {e}")
                        except Exception: pass
                threading.Thread(target=_go, daemon=True).start()
            except Exception as e:
                import traceback
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc())
                try: tg.send(chat, f"❌ Gadbad: {e}")
                except Exception: pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        print(f"\n  GADBAD: {e}\n  (log.txt Claude ko bhejo)")
        input("\n  Enter dabao...")
