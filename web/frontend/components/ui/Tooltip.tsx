"use client";
import { Tooltip as BaseTooltip } from "@base-ui/react/tooltip";
import type { ReactNode } from "react";
import { cn } from "./cn";

/**
 * TooltipProvider must be mounted once near the root of your app (e.g. in layout.tsx).
 * It manages shared hover delay across multiple tooltip instances.
 */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return <BaseTooltip.Provider>{children}</BaseTooltip.Provider>;
}

export function Tooltip({
  content,
  children,
}: {
  content: ReactNode;
  children: ReactNode;
}) {
  return (
    <BaseTooltip.Root>
      <BaseTooltip.Trigger
        render={<span />}
        className="inline-flex cursor-default"
      >
        {children}
      </BaseTooltip.Trigger>

      <BaseTooltip.Portal>
        <BaseTooltip.Positioner sideOffset={6}>
          <BaseTooltip.Popup
            className={cn(
              "rounded-md border border-border bg-surface px-2 py-1",
              "text-xs text-text shadow-lg",
            )}
          >
            {content}
          </BaseTooltip.Popup>
        </BaseTooltip.Positioner>
      </BaseTooltip.Portal>
    </BaseTooltip.Root>
  );
}
