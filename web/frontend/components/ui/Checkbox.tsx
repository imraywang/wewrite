"use client";
import { Checkbox as BaseCheckbox } from "@base-ui/react/checkbox";
import type { ReactNode } from "react";
import { cn } from "./cn";

export function Checkbox({
  checked,
  onCheckedChange,
  children,
  id,
  disabled,
}: {
  checked: boolean;
  onCheckedChange: (c: boolean) => void;
  children?: ReactNode;
  id?: string;
  disabled?: boolean;
}) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "inline-flex items-center gap-2 text-sm text-text",
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
      )}
    >
      <BaseCheckbox.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className={cn(
          "flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border border-border bg-surface-2",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
          "data-[checked]:bg-accent data-[checked]:border-accent",
          "data-[disabled]:opacity-50 data-[disabled]:pointer-events-none",
        )}
      >
        <BaseCheckbox.Indicator className="text-accent-fg">
          <svg
            width="10"
            height="8"
            viewBox="0 0 10 8"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M1 4L3.5 6.5L9 1"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </BaseCheckbox.Indicator>
      </BaseCheckbox.Root>
      {children}
    </label>
  );
}
