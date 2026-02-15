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
      <rect x="40" y="160" width="60" height="160" fill="#a5d8ff" opacity="0.4" />
      <rect x="110" y="130" width="45" height="190" fill="#a5d8ff" opacity="0.3" />
      <rect x="165" y="170" width="55" height="150" fill="#a5d8ff" opacity="0.4" />
      <rect x="230" y="100" width="40" height="220" fill="#a5d8ff" opacity="0.3" />
      <rect x="280" y="140" width="70" height="180" fill="#a5d8ff" opacity="0.4" />

      {/* CN Tower — Triangular Silhouette */}
      <path d="M530 300 L534 40 L536 40 L540 300 Z" fill="#99c9f0" />
      <circle cx="535" cy="100" r="16" fill="#99c9f0" />
      <rect x="520" y="98" width="30" height="5" rx="1" fill="#99c9f0" />
      <path d="M534 40 L535 15 L536 40 Z" fill="#99c9f0" />

      {/* Buildings right cluster */}
      <rect x="930" y="120" width="55" height="200" fill="#a5d8ff" opacity="0.2" />
      <rect x="995" y="160" width="45" height="160" fill="#a5d8ff" opacity="0.3" />
      <rect x="1050" y="100" width="60" height="220" fill="#a5d8ff" opacity="0.2" />
      <rect x="1120" y="140" width="50" height="180" fill="#a5d8ff" opacity="0.3" />

      {/* Ground base */}
      <rect x="0" y="300" width="1440" height="20" fill="#e5e7eb" opacity="0.5" />
    </svg>
  );
}

/* ─── Track lines ─── */
function Tracks() {
  return (
    <div className="absolute bottom-0 left-0 w-full">
      {/* Upper track */}
      <div className="absolute bottom-20 left-0 w-full h-[1px] bg-slate-300" />
      {/* Lower track */}
      <div className="absolute bottom-8 left-0 w-full h-[1px] bg-slate-300" />
      {/* Ground */}
      <div className="h-6 bg-[#f7f5e6] w-full" />
    </div>
  );
}

/* ─── Main Landing Page ─── */
export default function LandingPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#fdfcf0] landing-theme">
      {/* Paper texture overlay */}
      <div className="paper-grain" />

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
      <div className="relative z-20 flex flex-col items-start justify-center h-full px-12 md:px-24 pointer-events-none max-w-5xl">
        {/* Logo / Brand Name */}
        <div
          className={`transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <h1 className="text-6xl sm:text-7xl md:text-8xl font-black tracking-tighter uppercase text-slate-900">
            FluxRoute
          </h1>
        </div>

        {/* Slogan */}
        <div
          className={`mt-4 transition-all duration-1000 delay-200 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-slate-800 leading-tight">
            navigating toronto&apos;s <br />
            transit landscape with precision
          </h2>
        </div>

        {/* Tagline */}
        <div
          className={`mt-8 transition-all duration-1000 delay-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <p className="text-lg md:text-xl text-slate-600 max-w-2xl font-medium leading-relaxed">
            FluxRoute leverages machine learning and real-time data to <br />
            optimize your GTA commute through intelligent multimodal systems.
          </p>
        </div>

        {/* CTA Button */}
        <div
          className={`mt-10 transition-all duration-1000 delay-700 pointer-events-auto ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
            }`}
        >
          <Link href="/map">
            <button className="group relative px-8 py-3.5 rounded-md text-base font-bold text-white bg-slate-900 hover:bg-black transition-all duration-300">
              <span className="flex items-center gap-2">
                Launch System
                <svg
                  className="w-4 h-4 group-hover:translate-x-1 transition-transform"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={3}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
            </button>
          </Link>
        </div>

        {/* Subtle Hackathon credit */}
        <div
          className={`mt-24 transition-all duration-1000 delay-1000 ${mounted ? "opacity-80 translate-y-0" : "opacity-0 translate-y-4"
            }`}
        >
          <p className="text-xs font-black text-slate-900 tracking-[0.25em] uppercase">
            CTRL+HACK+DEL 2025
          </p>
        </div>
      </div>
    </div>
  );
}
