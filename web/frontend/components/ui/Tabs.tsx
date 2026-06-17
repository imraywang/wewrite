"use client";
import { Tabs as BaseTabs } from "@base-ui/react/tabs";
import type { ReactNode } from "react";
import { cn } from "./cn";

export function Tabs({
  value,
  onValueChange,
  items,
}: {
  value: string;
  onValueChange: (v: string) => void;
  items: { value: string; label: string; content: ReactNode }[];
}) {
  return (
    <BaseTabs.Root
      value={value}
      onValueChange={(v) => onValueChange(String(v))}
    >
      <BaseTabs.List
        className="inline-flex gap-1 rounded-md bg-surface-2 p-1"
      >
        {items.map((item) => (
          <BaseTabs.Tab
            key={item.value}
            value={item.value}
            className={cn(
              "rounded px-3 py-1.5 text-sm text-muted transition-colors",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
              "data-[active]:bg-surface data-[active]:text-text",
            )}
          >
            {item.label}
          </BaseTabs.Tab>
        ))}
      </BaseTabs.List>

      {items.map((item) => (
        <BaseTabs.Panel key={item.value} value={item.value} className="mt-3">
          {item.content}
        </BaseTabs.Panel>
      ))}
    </BaseTabs.Root>
  );
}
