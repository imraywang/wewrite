"use client";
import { Select as BaseSelect } from "@base-ui/react/select";
import { cn } from "./cn";

export type SelectOption = { value: string; label: string; description?: string };

export function Select({
  value,
  onValueChange,
  options,
  placeholder = "请选择…",
}: {
  value: string;
  onValueChange: (v: string) => void;
  options: SelectOption[];
  placeholder?: string;
}) {
  return (
    <BaseSelect.Root value={value} onValueChange={(v) => { if (v !== null) onValueChange(v); }}>
      <BaseSelect.Trigger
        className={cn(
          "inline-flex h-10 w-full items-center justify-between rounded-md border border-border",
          "bg-surface-2 px-3 text-sm text-text",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
          "data-[disabled]:opacity-50 data-[disabled]:pointer-events-none",
        )}
      >
        <BaseSelect.Value placeholder={placeholder} />
        <BaseSelect.Icon className="ml-2 opacity-60">▾</BaseSelect.Icon>
      </BaseSelect.Trigger>

      <BaseSelect.Portal>
        <BaseSelect.Positioner sideOffset={4}>
          <BaseSelect.Popup
            className={cn(
              "rounded-md border border-border bg-surface p-1 shadow-xl",
              "min-w-[var(--anchor-width)]",
            )}
          >
            <BaseSelect.List>
              {options.map((opt) => (
                <BaseSelect.Item
                  key={opt.value}
                  value={opt.value}
                  className={cn(
                    "group cursor-default rounded px-3 py-1.5 outline-none",
                    "data-[highlighted]:bg-surface-2",
                  )}
                >
                  <BaseSelect.ItemText className="block text-sm text-text group-data-[selected]:font-medium group-data-[selected]:text-accent">
                    {opt.label}
                  </BaseSelect.ItemText>
                  {opt.description ? (
                    <span className="mt-0.5 block text-xs leading-snug text-muted">
                      {opt.description}
                    </span>
                  ) : null}
                </BaseSelect.Item>
              ))}
            </BaseSelect.List>
          </BaseSelect.Popup>
        </BaseSelect.Positioner>
      </BaseSelect.Portal>
    </BaseSelect.Root>
  );
}
