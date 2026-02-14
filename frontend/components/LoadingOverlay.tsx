"use client";

export default function LoadingOverlay() {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0A0F1C]/80 backdrop-blur-sm">
      <div className="glass-card p-8 flex flex-col items-center gap-4">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
        </div>
        <div className="text-sm text-slate-300">Calculating routes...</div>
        <div className="flex gap-2">
          {["Transit", "Driving", "Walking"].map((mode) => (
            <div
              key={mode}
              className="h-2 w-16 bg-slate-700 rounded-full overflow-hidden"
            >
              <div className="h-full bg-blue-500 rounded-full pulse-glow" style={{ width: "60%" }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
