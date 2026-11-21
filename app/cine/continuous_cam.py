"""v3.30 CONTINUOUS CAMERA ENGINE (FFmpeg xfade Whip-Pan / Camera Slide / Zoom-Through).

Replaces hard jump-cut 'concat' joins with smooth, connected documentary camera movements
(slideleft, slideright, smoothup, zoomin, fade) batched in memory-safe groups of 5 shots
so an 8GB RAM Intel i5 laptop never runs out of memory.
Falls back cleanly to standard concat if any step fails.
"""
import subprocess
from pathlib import Path

from common import duration, log

# Tasteful documentary camera moves (no cheesy star-wipes)
CAM_MOVES = ("slideleft", "zoomin", "slideright", "smoothup", "dissolve")


def _xfade_batch(clips, out_path, td=0.26, start_idx=0, fps=30):
    """Join 2..6 clips with smooth xfade continuous-camera transitions."""
    if len(clips) == 1:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(clips[0]), "-c", "copy", str(out_path)],
            check=True, stdin=subprocess.DEVNULL,
        )
        return out_path

    durs = [max(0.4, duration(c) or 1.5) for c in clips]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for c in clips:
        cmd += ["-i", str(c)]

    fc = []
    # Normalize timebase & fps for every input so xfade never drifts
    for i in range(len(clips)):
        fc.append(f"[{i}:v]fps={fps},format=yuv420p,settb=AVTB[v{i}]")

    cur_label = "v0"
    cur_dur = durs[0]
    for i in range(1, len(clips)):
        eff_td = min(td, cur_dur * 0.35, durs[i] * 0.35)
        eff_td = max(0.12, round(eff_td, 3))
        offset = max(0.05, round(cur_dur - eff_td, 3))
        tr = CAM_MOVES[(start_idx + i - 1) % len(CAM_MOVES)]
        nxt = f"x{i}"
        fc.append(f"[{cur_label}][v{i}]xfade=transition={tr}:duration={eff_td}:offset={offset}[{nxt}]")
        cur_label = nxt
        cur_dur = offset + durs[i]

    cmd += [
        "-filter_complex", ";".join(fc),
        "-map", f"[{cur_label}]",
        "-an", "-c:v", "libx264", "-preset", "superfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-video_track_timescale", "15360",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL, timeout=240)
    return out_path


def join_continuous(shot_paths, out_mp4, work_dir, style=None, fps=30):
    """Join an arbitrary number of shots using batched Continuous-Camera xfade transitions.

    Returns True on success, False if caller should fall back to standard concat.
    """
    style = style or {}
    shots = [Path(p) for p in shot_paths if Path(p).exists() and Path(p).stat().st_size > 1000]
    if len(shots) < 2:
        return False

    td = float(style.get("camera_transition_sec", "0.26") or 0.26)
    td = max(0.14, min(0.45, td))
    work_dir = Path(work_dir)
    batch_size = 5  # Safe for 8GB RAM CPU!

    try:
        if len(shots) <= batch_size:
            _xfade_batch(shots, out_mp4, td=td, start_idx=0, fps=fps)
            log(f"   🎥 Continuous Camera: {len(shots)} shots smooth camera-pan/zoom se jude ✓")
            return True

        # Hierarchical 2-level batching (5 shots per group -> join groups with xfade)
        groups = []
        for gi, start in enumerate(range(0, len(shots), batch_size)):
            chunk = shots[start:start + batch_size]
            g_out = work_dir / f"cam_group_{gi:02d}.mp4"
            _xfade_batch(chunk, g_out, td=td, start_idx=start, fps=fps)
            groups.append(g_out)

        # Join groups seamlessly
        while len(groups) > batch_size:
            nxt_groups = []
            for gi, start in enumerate(range(0, len(groups), batch_size)):
                chunk = groups[start:start + batch_size]
                g_out = work_dir / f"cam_merge_{len(groups)}_{gi:02d}.mp4"
                _xfade_batch(chunk, g_out, td=td, start_idx=gi, fps=fps)
                nxt_groups.append(g_out)
            groups = nxt_groups

        _xfade_batch(groups, out_mp4, td=td, start_idx=len(shots), fps=fps)
        log(f"   🎥 Continuous Camera: {len(shots)} shots smooth camera-pan/zoom se jude ✓")
        return True
    except Exception as e:
        log(f"   (Continuous Camera fallback -> normal concat: {str(e)[:90]})", show=False)
        return False
