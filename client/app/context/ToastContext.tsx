"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id:       string;
  type:     ToastType;
  title:    string;
  message?: string;
}

interface ToastCtx {
  toasts:  ToastItem[];
  toast:   (type: ToastType, title: string, message?: string) => void;
  dismiss: (id: string) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback(
    (type: ToastType, title: string, message?: string) => {
      const id = Math.random().toString(36).slice(2, 10);
      setToasts((p) => [...p, { id, type, title, message }]);
      setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 4500);
    },
    [],
  );

  const dismiss = useCallback((id: string) => {
    setToasts((p) => p.filter((t) => t.id !== id));
  }, []);

  return (
    <Ctx.Provider value={{ toasts, toast, dismiss }}>{children}</Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
