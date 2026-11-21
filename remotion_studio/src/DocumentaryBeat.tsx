import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface BeatProps {
  kind?: "news_highlight" | "stat_slam" | "cutout_3d" | "timeline_3d";
  source?: string;
  headline?: string;
  highlight?: string;
  value?: string;
  label?: string;
  sub?: string;
  stamp?: string;
  dateStr?: string;
  durationInFrames?: number;
}

export const DocumentaryBeat: React.FC<BeatProps> = ({
  kind = "news_highlight",
  source = "FACT REPORT",
  headline = "Verified Documentary Brief",
  highlight = "",
  value = "900M",
  label = "KEY DATA",
  sub = "",
  stamp = "",
  dateStr = "DOCUMENTARY • v3.30",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 120, mass: 0.9 } });
  const drift = interpolate(frame, [0, durationInFrames], [1.0, 1.07]);
  const camRotY = interpolate(frame, [0, durationInFrames], [-3.2, 2.4]);
  const hlSweep = spring({ frame: Math.max(0, frame - 14), fps, config: { damping: 18, stiffness: 90 } });
  const stampSpring = spring({ frame: Math.max(0, frame - 16), fps, config: { damping: 10, stiffness: 220 } });

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(circle at 50% 42%, #1a2436 0%, #0b0f17 72%, #05070b 100%)",
        fontFamily: "'Noto Sans Devanagari', 'Poppins', 'Montserrat', sans-serif",
        justifyContent: "center",
        alignItems: "center",
        perspective: 1200,
        overflow: "hidden",
      }}
    >
      {/* Subtle Blueprint Grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(130,180,235,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(130,180,235,0.08) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          transform: `scale(${1 + (drift - 1) * 0.5})`,
        }}
      />

      {/* 3D Camera Container */}
      <div
        style={{
          width: "86%",
          transform: `scale(${(0.88 + 0.12 * enter) * drift}) rotateY(${camRotY}deg) translateY(${(1 - enter) * 60}px)`,
          transformStyle: "preserve-3d",
          opacity: Math.min(1, frame / 6),
        }}
      >
        {kind === "stat_slam" ? (
          <div style={{ textAlign: "center", position: "relative" }}>
            {stamp ? (
              <div
                style={{
                  display: "inline-block",
                  marginBottom: 34,
                  padding: "10px 34px",
                  border: "8px solid #e62e2e",
                  borderRadius: 14,
                  color: "#ff3b3b",
                  background: "rgba(180,20,20,0.22)",
                  fontSize: 64,
                  fontWeight: 900,
                  letterSpacing: 4,
                  transform: `rotate(-10deg) scale(${1.7 - 0.7 * stampSpring})`,
                  opacity: frame >= 16 ? 1 : 0,
                  boxShadow: "0 18px 40px rgba(230,46,46,0.35)",
                }}
              >
                {stamp}
              </div>
            ) : null}
            <div
              style={{
                fontSize: 138,
                fontWeight: 900,
                color: "#ffd400",
                textShadow: "0 0 42px rgba(255,212,0,0.45), 0 12px 24px rgba(0,0,0,0.7)",
                lineHeight: 1.05,
              }}
            >
              {value}
            </div>
            <div
              style={{
                display: "inline-block",
                marginTop: 28,
                padding: "14px 36px",
                borderRadius: 16,
                background: "rgba(255,255,255,0.09)",
                border: "2px solid rgba(255,212,0,0.45)",
                color: "#ffffff",
                fontSize: 44,
                fontWeight: 800,
                letterSpacing: 2,
              }}
            >
              {label}
            </div>
            {sub ? (
              <div style={{ marginTop: 26, color: "#cfd8e6", fontSize: 34, fontWeight: 500 }}>
                {sub}
              </div>
            ) : null}
          </div>
        ) : (
          /* News / Fact Highlighter Card with 3D Shadow & Yellow Marker Sweep */
          <div
            style={{
              background: "#faf7f0",
              borderRadius: 24,
              padding: "46px 48px 54px",
              boxShadow: "0 36px 80px rgba(0,0,0,0.65)",
              borderTop: "14px solid #c62828",
            }}
          >
            <div style={{ color: "#b71c1c", fontSize: 36, fontWeight: 900, letterSpacing: 1.5 }}>
              {source}
            </div>
            <div style={{ color: "#686c75", fontSize: 24, marginTop: 6, marginBottom: 24 }}>
              {dateStr}
            </div>
            <div style={{ height: 2, background: "#dcd6ca", marginBottom: 30 }} />
            <div style={{ color: "#151820", fontSize: 48, fontWeight: 800, lineHeight: 1.38, position: "relative" }}>
              <span
                style={{
                  position: "relative",
                  display: "inline",
                  backgroundImage: "linear-gradient(90deg, #ffe036 0%, #ffe036 100%)",
                  backgroundRepeat: "no-repeat",
                  backgroundSize: `${Math.round(hlSweep * 100)}% 88%`,
                  backgroundPosition: "0 75%",
                  padding: "2px 8px",
                  borderRadius: 8,
                }}
              >
                {highlight || headline}
              </span>
              {highlight && headline !== highlight ? ` — ${headline}` : ""}
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
