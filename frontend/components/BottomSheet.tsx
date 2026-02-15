"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface BottomSheetProps {
  children: React.ReactNode;
  onClose: () => void;
}

const SNAP_POINTS = [0.3, 0.6, 0.95]; // Percentage of viewport height
const VELOCITY_THRESHOLD = 0.5; // px/ms for fast swipe

export default function BottomSheet({ children, onClose }: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [snapIndex, setSnapIndex] = useState(1); // Start at 60%
  const [dragging, setDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);

  const dragStartY = useRef(0);
  const dragStartTime = useRef(0);
  const lastY = useRef(0);

  const sheetHeight = typeof window !== "undefined"
    ? window.innerHeight * SNAP_POINTS[snapIndex]
    : 400;

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    // Only handle drag from the handle area, not scrollable content
    const target = e.target as HTMLElement;
    if (contentRef.current?.contains(target) && contentRef.current.scrollTop > 0) return;

    dragStartY.current = e.touches[0].clientY;
    dragStartTime.current = Date.now();
    lastY.current = e.touches[0].clientY;
    setDragging(true);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!dragging) return;
    const currentY = e.touches[0].clientY;
    const delta = currentY - dragStartY.current;
    setDragOffset(delta);
    lastY.current = currentY;
  }, [dragging]);

  const handleTouchEnd = useCallback(() => {
    if (!dragging) return;
    setDragging(false);

    const elapsed = Date.now() - dragStartTime.current;
    const velocity = dragOffset / elapsed; // px/ms

    let targetIndex = snapIndex;

    if (Math.abs(velocity) > VELOCITY_THRESHOLD) {
      // Fast swipe
      if (velocity > 0) {
        // Swiping down
        targetIndex = snapIndex > 0 ? snapIndex - 1 : -1;
      } else {
        // Swiping up
        targetIndex = Math.min(snapIndex + 1, SNAP_POINTS.length - 1);
      }
    } else {
      // Slow drag: snap to nearest
      const currentHeight = window.innerHeight * SNAP_POINTS[snapIndex] - dragOffset;
      const currentPercent = currentHeight / window.innerHeight;

      let closest = 0;
      let closestDist = Infinity;
      for (let i = 0; i < SNAP_POINTS.length; i++) {
        const dist = Math.abs(SNAP_POINTS[i] - currentPercent);
        if (dist < closestDist) {
          closestDist = dist;
          closest = i;
        }
      }
      targetIndex = closest;
    }

    if (targetIndex < 0) {
      onClose();
    } else {
      setSnapIndex(targetIndex);
    }
    setDragOffset(0);
  }, [dragging, dragOffset, snapIndex, onClose]);

  // Keyboard escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const displayHeight = Math.max(0, sheetHeight - dragOffset);

  return (
    <>
      {/* Backdrop (only at full height) */}
      {snapIndex >= 2 && (
        <div
          className="fixed inset-0 z-30 bg-black/20 fade-backdrop"
          onClick={onClose}
        />
      )}

      {/* Sheet */}
      <div
        ref={sheetRef}
        className="fixed bottom-0 left-0 right-0 z-30 panel-glass rounded-t-2xl shadow-2xl border-t border-[var(--glass-border)]"
        style={{
          height: displayHeight,
          transition: dragging ? "none" : "height 0.3s ease-out",
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        role="dialog"
        aria-label="Route details"
      >
        {/* Drag handle */}
        <div className="flex justify-center py-2 cursor-grab active:cursor-grabbing">
          <div className="w-10 h-1 rounded-full bg-[var(--text-muted)] opacity-40" />
        </div>

        {/* Scrollable content */}
        <div
          ref={contentRef}
          className="overflow-y-auto"
          style={{ height: `calc(100% - 20px)` }}
        >
          {children}
        </div>
      </div>
    </>
  );
}
