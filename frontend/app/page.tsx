"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";

/* ─── Inline SVG: Toronto Skyline Silhouette ─── */
function Skyline() {
  return (
    <svg
      className="absolute bottom-24 left-0 w-full"
      viewBox="0 0 1440 320"
      preserveAspectRatio="none"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Buildings left cluster */}
      <rect x="40" y="160" width="60" height="160" fill="#1e293b" />
      <rect x="110" y="130" width="45" height="190" fill="#1a2332" />
      <rect x="165" y="170" width="55" height="150" fill="#1e293b" />
      <rect x="230" y="100" width="40" height="220" fill="#1a2332" />
      <rect x="280" y="140" width="70" height="180" fill="#1e293b" />

      {/* Rogers Centre dome */}
      <ellipse cx="420" cy="240" rx="60" ry="30" fill="#1a2332" />
      <rect x="360" y="240" width="120" height="80" fill="#1a2332" />

      {/* CN Tower */}
      <rect x="530" y="20" width="8" height="300" fill="#253347" />
      <rect x="524" y="30" width="20" height="6" fill="#253347" />
      <ellipse cx="534" cy="100" rx="18" ry="22" fill="#253347" />
      <rect x="520" y="90" width="28" height="30" fill="#253347" />
      {/* CN Tower beacon */}
      <circle cx="534" cy="20" r="3" fill="#ef4444" className="cn-beacon" />

      {/* Buildings center cluster */}
      <rect x="590" y="110" width="50" height="210" fill="#1e293b" />
      <rect x="650" y="80" width="55" height="240" fill="#1a2332" />
      <rect x="715" y="130" width="45" height="190" fill="#1e293b" />
      <rect x="770" y="90" width="60" height="230" fill="#253347" />
      <rect x="840" y="150" width="50" height="170" fill="#1e293b" />

      {/* Buildings right cluster */}
      <rect x="930" y="120" width="55" height="200" fill="#1a2332" />
      <rect x="995" y="160" width="45" height="160" fill="#1e293b" />
      <rect x="1050" y="100" width="60" height="220" fill="#253347" />
      <rect x="1120" y="140" width="50" height="180" fill="#1a2332" />
      <rect x="1180" y="170" width="65" height="150" fill="#1e293b" />
      <rect x="1255" y="130" width="50" height="190" fill="#1a2332" />
      <rect x="1315" y="155" width="55" height="165" fill="#1e293b" />
      <rect x="1380" y="180" width="60" height="140" fill="#1a2332" />

      {/* Window lights — scattered warm dots */}
      {[
        [70, 180], [75, 200], [80, 220], [85, 240],
        [130, 150], [135, 170], [140, 195], [130, 220],
        [250, 120], [245, 145], [250, 170], [255, 200],
        [300, 160], [310, 185], [320, 210], [305, 240],
        [610, 130], [615, 155], [605, 180], [615, 210],
        [670, 100], [680, 125], [675, 150], [680, 180], [670, 210],
        [735, 150], [740, 175], [730, 200],
        [790, 110], [800, 135], [795, 165], [800, 195], [790, 225],
        [860, 170], [855, 195], [865, 220],
        [950, 140], [955, 165], [945, 195], [950, 225],
        [1070, 120], [1075, 150], [1065, 180], [1075, 210],
        [1140, 160], [1145, 185], [1135, 215],
        [1200, 190], [1210, 215], [1205, 240],
        [1275, 150], [1270, 175], [1280, 200],
        [1335, 175], [1340, 200], [1330, 225],
      ].map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r="2"
          fill="#fbbf24"
          opacity={0.3 + (i % 3) * 0.25}
          className={i % 4 === 0 ? "window-twinkle" : ""}
        />
      ))}

      {/* Ground base */}
      <rect x="0" y="300" width="1440" height="20" fill="#0f172a" />
    </svg>
  );
}

/* ─── Track lines ─── */
function Tracks() {
  return (
    <div className="absolute bottom-0 left-0 w-full">
      {/* Upper track (GO Train) */}
      <div className="absolute bottom-20 left-0 w-full">
        <div className="h-[2px] bg-slate-700/60 w-full" />
        <div className="h-[2px] bg-slate-700/40 w-full mt-[6px]" />
      </div>
      {/* Lower track (Subway) */}
      <div className="absolute bottom-8 left-0 w-full">
        <div className="h-[2px] bg-slate-700/60 w-full" />
        <div className="h-[2px] bg-slate-700/40 w-full mt-[6px]" />
      </div>
      {/* Ground */}
      <div className="h-6 bg-[#0f172a] w-full" />
    </div>
  );
}

/* ─── Main Landing Page ─── */
export default function LandingPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    document.documentElement.dataset.theme = "dark";
  }, []);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#0a0f1c]">
      {/* Sky gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#0a0f1c] via-[#0f1729] to-[#131b2e]" />

      {/* Subtle stars */}
      <div className="absolute inset-0 overflow-hidden">
        {mounted &&
          Array.from({ length: 40 }).map((_, i) => (
            <div
              key={i}
              className="absolute rounded-full bg-white star-twinkle"
              style={{
                width: `${1 + (i % 3)}px`,
                height: `${1 + (i % 3)}px`,
                top: `${5 + ((i * 7 + 13) % 45)}%`,
                left: `${(i * 13 + 7) % 100}%`,
                animationDelay: `${(i * 0.7) % 4}s`,
                opacity: 0.4 + (i % 3) * 0.2,
              }}
            />
          ))}
      </div>

      {/* Skyline */}
      <Skyline />

      {/* Tracks */}
      <Tracks />

      {/* Upper GO Train — moves left to right */}
      <div className="train-go absolute bottom-[80px] z-10">
        <Image
          src="/images/go-train.svg"
          alt="GO Train"
          width={1000}
          height={128}
          className="h-28 w-auto"
          draggable={false}
          priority
        />
      </div>

      {/* Lower GO Train — moves right to left */}
      <div className="train-subway absolute bottom-[32px] z-10">
        <Image
          src="/images/go-train.svg"
          alt="GO Train"
          width={1000}
          height={128}
          className="h-28 w-auto"
          draggable={false}
          priority
        />
      </div>

      {/* Hero content */}
      <div className="relative z-20 flex flex-col items-center justify-center h-full px-4 pointer-events-none">
        {/* Logo / Title */}
        <div
          className={`transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <h1 className="text-6xl sm:text-7xl md:text-8xl font-bold tracking-tight text-center">
            <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent">
              Flux
            </span>
            <span className="text-white">Route</span>
          </h1>
        </div>

        {/* Tagline */}
        <div
          className={`transition-all duration-1000 delay-300 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <p className="mt-4 text-lg sm:text-xl md:text-2xl text-slate-400 text-center max-w-2xl leading-relaxed">
            AI-Powered Multimodal Transit Routing
            <br />
            <span className="text-slate-500">for the Greater Toronto Area</span>
          </p>
        </div>

        {/* Feature pills */}
        <div
          className={`transition-all duration-1000 delay-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {[
              "ML Delay Predictions",
              "Real-Time GTFS",
              "Traffic Analysis",
              "AI Chat Assistant",
            ].map((feature) => (
              <span
                key={feature}
                className="px-4 py-1.5 rounded-full text-sm text-slate-300 border border-slate-700/50 bg-slate-800/40 backdrop-blur-sm"
              >
                {feature}
              </span>
            ))}
          </div>
        </div>

        {/* CTA Button */}
        <div
          className={`transition-all duration-1000 delay-700 pointer-events-auto ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <Link href="/map">
            <button className="mt-10 group relative px-8 py-4 rounded-xl text-lg font-semibold text-white bg-blue-600/80 backdrop-blur-md border border-blue-400/30 hover:bg-blue-500/90 hover:border-blue-400/50 hover:scale-105 active:scale-95 transition-all duration-300 cta-glow">
              <span className="flex items-center gap-2">
                Start Your Journey
                <svg
                  className="w-5 h-5 group-hover:translate-x-1 transition-transform"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
            </button>
          </Link>
        </div>

        {/* Subtle Hackathon credit — now below CTA */}
        <div
          className={`mt-12 transition-all duration-1000 delay-1000 ${mounted ? "opacity-90 translate-y-0" : "opacity-0 translate-y-4"
            }`}
        >
          <p className="text-sm font-black text-slate-100 tracking-[0.2em] uppercase">
            CTRL+HACK+DEL 2025
          </p>
        </div>
      </div>
    </div>
  );
}
