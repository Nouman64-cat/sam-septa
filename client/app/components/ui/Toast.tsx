"use client";

import { useToast, type ToastType } from "../../context/ToastContext";

// ── Per-type styling ──────────────────────────────────────────────────────────

const META: Record<ToastType, { bg: string; icon: string }> = {
  success: { bg: "bg-emerald-600", icon: "✓" },
  error:   { bg: "bg-red-600",     icon: "✕" },
  info:    { bg: "bg-blue-600",    icon: "ℹ" },
  warning: { bg: "bg-amber-500",   icon: "⚠" },
};

// ── Component ─────────────────────────────────────────────────────────────────

export function ToastContainer() {
  const { toasts, dismiss } = useToast();

  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 w-80 pointer-events-none">
      {toasts.map((t) => {
        const { bg, icon } = META[t.type];
        return (
          <div
            key={t.id}
            className={[
              bg,
              "pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3.5",
              "text-white shadow-2xl animate-toast",
            ].join(" ")}
          >
            {/* Icon */}
            <span className="text-sm font-bold leading-5 mt-px shrink-0 opacity-90">
              {icon}
            </span>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold leading-5">{t.title}</p>
              {t.message && (
                <p className="text-xs opacity-75 mt-0.5 break-words leading-4">
                  {t.message}
                </p>
              )}
            </div>

            {/* Dismiss */}
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss notification"
              className="shrink-0 opacity-50 hover:opacity-90 transition-opacity text-xs leading-5 mt-px"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
