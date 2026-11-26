"""v4.17 ZERO-TEMPLATE DYNAMIC AI HTML5/CANVAS/SVG 30FPS EXPLAINER ENGINE.

Triggered by script tag:
  [explain: <any complex concept, mechanism, process, comparison, or timeline>]
  [anim: <any visual explanation>]

How it works ($0 FREE, zero external pip/npm dependencies):
  1. Gemini / Groq (via app/ai.py) writes a brand-new, self-contained HTML5 Canvas/SVG
     animation tailored to THAT exact line (ZERO fixed templates!) exposing `window.renderAt(t)`.
  2. A pure-Python Chrome DevTools Protocol (CDP) driver steps `window.renderAt(t)` frame-by-frame
     at 30fps in headless Chrome/Chromium and pipes crisp PNG frames directly into FFmpeg.
  3. Strict Visual Quality Gate checks mid-frame variance & detail before encoding; if anything
     fails or looks blank, returns None silently so the untouched Visual Search Engine handles it.
"""
import base64
import hashlib
import io
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from common import log


def _find_chrome():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


# ------------------------------------------------------------------ Minimal Pure-Python WebSocket (RFC6455) for CDP
class _CDPClient:
    def __init__(self, ws_url, timeout=15.0):
        m = re.match(r"^ws://([^:/]+):(\d+)(/.*)$", ws_url)
        if not m:
            raise RuntimeError(f"Bad WS URL: {ws_url}")
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WS handshake closed")
            buf += chunk
        self._extra = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _recv_exact(self, n):
        out = bytearray()
        if self._extra:
            take = min(n, len(self._extra))
            out.extend(self._extra[:take])
            self._extra = self._extra[take:]
        while len(out) < n:
            chunk = self.sock.recv(min(65536, n - len(out)))
            if not chunk:
                raise RuntimeError("WS EOF")
            out.extend(chunk)
        return bytes(out)

    def _send_text(self, s):
        data = s.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        ln = len(data)
        if ln < 126:
            header.append(0x80 | ln)
        elif ln < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", ln))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", ln))
        header.extend(mask)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def _recv_msg(self):
        chunks = []
        while True:
            b1, b2 = self._recv_exact(2)
            fin = (b1 & 0x80) != 0
            opcode = b1 & 0x0F
            masked = (b2 & 0x80) != 0
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack("!H", self._recv_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else None
            payload = self._recv_exact(ln)
            if mask:
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            if opcode == 8:
                raise RuntimeError("WS closed by Chrome")
            if opcode == 9:  # ping -> pong
                continue
            chunks.append(payload)
            if fin:
                return b"".join(chunks).decode("utf-8", errors="replace")

    def call(self, method, params=None):
        self._id += 1
        cid = self._id
        self._send_text(json.dumps({"id": cid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self._recv_msg())
            if msg.get("id") == cid:
                if "error" in msg:
                    raise RuntimeError(str(msg["error"]))
                return msg.get("result") or {}

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------ AI Dynamic HTML5 Motion-Graphics Generator
_SYSTEM_PROMPT = """You are a Vox / Kurzgesagt / Nitish Rajput 30fps Motion-Graphics Engineer.
Write a COMPLETE, SELF-CONTAINED HTML5 file that renders a cinema-grade animated visual explanation for the given scene.

STRICT TECHNICAL REQUIREMENTS:
1. Viewport is EXACTLY {W}x{H} pixels (overflow:hidden; margin:0; background:#060a14;).
2. ZERO external URLs, ZERO CDN scripts, ZERO external fonts or images (100% offline-safe pure HTML5 Canvas 2D / SVG).
3. MUST define a global deterministic function:
     window.renderAt = function(t) {{ ... }};
   where `t` is elapsed time in seconds from `0.0` to `{DUR:.2f}`.
   Every call to `window.renderAt(t)` MUST immediately redraw the entire {W}x{H} canvas/SVG for timestamp `t` (NO requestAnimationFrame dependency!). Also call `window.renderAt(0)` once on load.
4. VISUAL QUALITY (VIRAL INDIAN DOCUMENTARY — DHRUV RATHEE / VOX / CUTTING-MAT LOOK):
   - Rich tactile dark editorial background (#0d1117 -> #06090f) with subtle drafting grid or warm archival paper card contrast.
   - Use proven viral documentary visual devices tailored SPECIFICALLY to this scene:
     * For numbers/money/percentages: smooth rolling animated counters, crisp comparison tables with animated translucent YELLOW HIGHLIGHTER SWEEP (#FFE135), and red hand-drawn marker circle callouts around key peaks/drops.
     * For science/tech/mechanisms: clear step-by-step animated cross-sections, flowing directional arrows, labeled components, and soft glowing highlights.
     * For geography/comparisons: clean split-screen divider line with bold badges popping in with cubic ease-out.
   - Keep ALL important elements safely inside central 82% margin (never clipped, never overlapping text!).
   - Use crisp bold sans-serif English/digit labels (`system-ui, Arial, sans-serif`) sized appropriately for {W}x{H} (minimum 30px).
5. Return ONLY raw HTML starting with `<!DOCTYPE html>` and ending with `</html>` (no markdown fences, no commentary)."""


def generate_html_scene(scene_desc, hindi_line, W, H, dur, keys):
    """Ask Gemini / Groq to write a brand-new zero-template HTML5 animated explainer for this exact line."""
    try:
        import ai
        key = (keys or {}).get("GEMINI") or ""
        if not key and not (ai.BACKUP["keys"].get("GROQ") or ai.BACKUP["keys"].get("OPENROUTER")):
            return None
        prompt = (
            _SYSTEM_PROMPT.format(W=W, H=H, DUR=float(dur))
            + f"\n\nSCENE TO ANIMATE IN DETAIL: {scene_desc}\n"
            + (f"NARRATION CONTEXT (Hindi): {hindi_line}\n" if hindi_line else "")
            + "\nBuild a vivid, clear, step-by-step animated visual explanation that makes a viewer instantly understand this exact concept!"
        )
        raw = ai.ask(key, [prompt], temperature=0.35, timeout=55)
        if not raw:
            return None
        txt = re.sub(r"^```[a-zA-Z]*\s*", "", raw.strip())
        txt = re.sub(r"\s*```$", "", txt.strip())
        m = re.search(r"(<!DOCTYPE html[\s\S]*?</html>|<html[\s\S]*?</html>)", txt, re.I)
        if not m:
            return None
        html = m.group(1)
        if "renderAt" not in html:
            return None
        return html
    except Exception as e:
        log(f"   (ai_explainer HTML gen skip: {str(e)[:80]})", show=False)
        return None


def _frame_quality_ok(png_bytes):
    """Strict Visual Quality Gate: reject blank/solid/broken renders."""
    try:
        with Image.open(io.BytesIO(png_bytes)) as im:
            gray = np.asarray(im.convert("L").resize((256, 256)), dtype=np.float32)
            std = float(gray.std())
            if std < 11.0:
                return False, f"blank/flat frame (std={std:.1f})"
            lap = (
                -4.0 * gray[1:-1, 1:-1]
                + gray[:-2, 1:-1] + gray[2:, 1:-1]
                + gray[1:-1, :-2] + gray[1:-1, 2:]
            )
            sharp = float(lap.var())
            if sharp < 12.0:
                return False, f"low-detail frame (sharp={sharp:.1f})"
            return True, "ok"
    except Exception as e:
        return False, str(e)


def render_html_to_mp4(html_str, out_mp4, W, H, dur, style=None, fps=30):
    """Render deterministic HTML5 `window.renderAt(t)` animation to 30fps HD MP4 via headless Chrome CDP."""
    chrome_bin = _find_chrome()
    if not chrome_bin:
        log("   (ai_explainer skip: Chrome/Chromium not installed)", show=False)
        return None

    dur = max(2.0, min(7.0, float(dur or 3.8)))
    total_frames = max(20, int(round(dur * fps)))
    tmp_dir = Path(tempfile.mkdtemp(prefix="vg_aiexp_"))
    html_file = tmp_dir / "scene.html"
    html_file.write_text(html_str, encoding="utf-8")

    # Pick a free local port for CDP
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    chrome_cmd = [
        chrome_bin,
        "--headless=new",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        f"--window-size={W},{H}",
        f"--remote-debugging-port={port}", "--remote-allow-origins=*",
        f"--user-data-dir={tmp_dir / 'prof'}",
        "about:blank",
    ]
    chrome_proc = None
    cdp = None
    ff_proc = None
    try:
        chrome_proc = subprocess.Popen(
            chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
        )
        ws_url = None
        for _ in range(40):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1.5) as resp:
                    tabs = json.loads(resp.read().decode("utf-8"))
                    for tab in tabs:
                        if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                            ws_url = tab["webSocketDebuggerUrl"]
                            break
                if ws_url:
                    break
            except Exception:
                time.sleep(0.15)
        if not ws_url:
            raise RuntimeError("Chrome CDP did not start")

        cdp = _CDPClient(ws_url, timeout=20.0)
        cdp.call("Page.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": W, "height": H, "deviceScaleFactor": 1, "mobile": False
        })
        ft = cdp.call("Page.getFrameTree")
        fid = ft["frameTree"]["frame"]["id"]
        cdp.call("Page.setDocumentContent", {"frameId": fid, "html": html_str})
        time.sleep(0.15)
        chk = cdp.call("Runtime.evaluate", {
            "expression": f"(typeof window.renderAt === 'function') ? (window.renderAt({dur * 0.55:.3f}), 'OK') : 'WAIT'",
            "returnByValue": True,
        })
        if (chk.get("result") or {}).get("value") != "OK":
            raise RuntimeError("renderAt function missing or errored")

        mid_shot = cdp.call("Page.captureScreenshot", {"format": "png"})
        mid_png = base64.b64decode(mid_shot["data"])
        q_ok, q_why = _frame_quality_ok(mid_png)
        if not q_ok:
            log(f"   🧹 ai_explainer QC reject ({q_why}) -> falling back safely", show=False)
            return None

        # Pipe all frames directly into FFmpeg
        try:
            from render import enc_args
            e_args = enc_args(style or {})
        except Exception:
            e_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p"]

        ff_cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "image2pipe", "-vcodec", "png", "-r", str(fps), "-i", "-",
            "-vf", f"scale={W}:{H}", "-an",
        ] + e_args + [str(out_mp4)]
        ff_proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)

        for i in range(total_frames):
            t_sec = i / fps
            cdp.call("Runtime.evaluate", {"expression": f"window.renderAt({t_sec:.4f});"})
            shot = cdp.call("Page.captureScreenshot", {"format": "png"})
            ff_proc.stdin.write(base64.b64decode(shot["data"]))

        ff_proc.stdin.close()
        if ff_proc.wait() != 0:
            raise RuntimeError("FFmpeg encode failed")
        return str(out_mp4)
    except Exception as e:
        log(f"   (ai_explainer render skip: {str(e)[:90]})", show=False)
        return None
    finally:
        if cdp:
            cdp.close()
        if ff_proc and ff_proc.poll() is None:
            try:
                ff_proc.kill()
            except Exception:
                pass
        if chrome_proc:
            try:
                chrome_proc.terminate()
                chrome_proc.wait(timeout=3)
            except Exception:
                try:
                    chrome_proc.kill()
                except Exception:
                    pass
        shutil.rmtree(tmp_dir, ignore_errors=True)


def render_explainer(scene_desc, hindi_line, dur, out_mp4, W, H, style, keys, fps=30):
    """End-to-end zero-template dynamic AI HTML5 30fps explainer -> MP4 (returns path or None)."""
    html = generate_html_scene(scene_desc, hindi_line, W, H, dur, keys)
    if not html:
        return None
    res = render_html_to_mp4(html, out_mp4, W, H, dur, style=style, fps=fps)
    if res:
        log(f"   ✨ AI dynamic 30fps explainer ready: {str(scene_desc)[:55]}", show=False)
    return res
