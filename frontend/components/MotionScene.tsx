"use client";

import { MotionConfig } from "framer-motion";

export function MotionScene({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <div className="ambient-scene" aria-hidden="true">
        <div className="aurora aurora-violet" />
        <div className="aurora aurora-cyan" />
        <div className="ambient-grid" />
        <svg className="constellation-field" viewBox="0 0 1600 950" preserveAspectRatio="xMidYMid slice"><g fill="none" stroke="#3754ad" strokeWidth=".6" opacity=".22"><path d="M0 220L140 290L60 420L340 550L780 120L780 0M1600 200L1400 60L1200 200L1440 430L1600 370M0 800L100 860L420 760L640 950M100 860V950M1400 60V0" /></g>{[[140,290],[60,420],[780,120],[1400,60],[1200,200],[100,860],[420,760],[40,750],[810,300]].map(([x,y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="2" fill="#527aff" opacity=".55" />)}</svg>
        <div className="digital-globe"><svg viewBox="0 0 500 500"><defs><radialGradient id="globe-fade"><stop stopColor="#5261ef" stopOpacity=".12" /><stop offset="1" stopColor="#1d3b96" stopOpacity=".03" /></radialGradient></defs><circle cx="250" cy="250" r="240" fill="url(#globe-fade)" stroke="#6669f5" strokeOpacity=".2" />{[60,110,160,205,235].map(rx => <ellipse key={rx} cx="250" cy="250" rx={rx} ry="240" fill="none" stroke="#4d62d6" strokeOpacity=".3" strokeDasharray="1 6" />)}{[70,130,190,250,310,370,430].map(y => <ellipse key={y} cx="250" cy={y} rx={Math.sqrt(240*240-(y-250)*(y-250))} ry="35" fill="none" stroke="#456eea" strokeOpacity=".35" strokeDasharray="1 5" />)}{Array.from({length:400},(_,i) => {const a=i*2.39996;const r=Math.sqrt(i/400)*233;return <circle key={i} cx={250+Math.cos(a)*r} cy={250+Math.sin(a)*r} r={i%5===0?1.4:.7} fill={i%3===0?"#23adff":"#6264ec"} opacity=".5" />;})}</svg></div>
      </div>
      {children}
    </MotionConfig>
  );
}
