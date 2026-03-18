"use client";

import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Visible label rendered above the input. */
  label: string;
  /** Helper text shown below when there is no error. */
  hint?: string;
  /** Validation error replaces the hint and turns the border red. */
  error?: string;
  /** Must be provided; used to associate label + input for accessibility. */
  id: string;
}

export function Input({
  label,
  hint,
  error,
  id,
  className = "",
  ...rest
}: InputProps) {
  const borderClass = error
    ? "border-red-400 bg-red-50 focus-visible:ring-red-400"
    : "border-gray-300 bg-white focus-visible:ring-blue-500";

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-gray-700">
        {label}
      </label>

      <input
        id={id}
        className={[
          "rounded-lg border px-3 py-2 text-sm text-gray-900",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
          "transition-colors placeholder:text-gray-400",
          borderClass,
          className,
        ].join(" ")}
        {...rest}
      />

      {error && <p className="text-xs text-red-500">{error}</p>}
      {!error && hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
}
