import type { ScraperStatus } from "../../types";
import { Spinner } from "./Spinner";

interface Config {
  label: string;
  classes: string;
  icon: "spinner" | "check" | "cross" | "stop" | "dot";
}

const STATUS_CONFIG: Record<ScraperStatus, Config> = {
  idle: {
    label: "Idle",
    classes: "bg-gray-100 text-gray-500",
    icon: "dot",
  },
  running: {
    label: "Running",
    classes: "bg-blue-100 text-blue-700",
    icon: "spinner",
  },
  done: {
    label: "Done",
    classes: "bg-green-100 text-green-700",
    icon: "check",
  },
  stopped: {
    label: "Stopped",
    classes: "bg-amber-100 text-amber-700",
    icon: "stop",
  },
  error: {
    label: "Error",
    classes: "bg-red-100 text-red-700",
    icon: "cross",
  },
};

interface StatusBadgeProps {
  status: ScraperStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, classes, icon } = STATUS_CONFIG[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${classes}`}
    >
      {icon === "spinner" && <Spinner size="sm" />}
      {icon === "check"   && <span aria-hidden>&#10003;</span>}
      {icon === "cross"   && <span aria-hidden>&#10005;</span>}
      {icon === "stop"    && <span aria-hidden>&#9632;</span>}
      {icon === "dot"     && (
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400" aria-hidden />
      )}
      {label}
    </span>
  );
}
