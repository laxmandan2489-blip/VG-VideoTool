import React from "react";
import { Composition } from "remotion";
import { DocumentaryBeat } from "./DocumentaryBeat";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="DocumentaryBeat"
      component={DocumentaryBeat}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        kind: "news_highlight",
        source: "THE VIRAL GYAAN",
        headline: "Documentary Mode Active",
        highlight: "Documentary Mode",
      }}
    />
  );
};
