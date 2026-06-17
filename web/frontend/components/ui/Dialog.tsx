"use client";
import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ReactNode } from "react";
import { cn } from "./cn";

export function Dialog({
  trigger,
  title,
  children,
  open,
  onOpenChange,
}: {
  trigger?: ReactNode;
  title?: ReactNode;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  return (
    <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? (
        <BaseDialog.Trigger render={<span />}>{trigger}</BaseDialog.Trigger>
      ) : null}

      <BaseDialog.Portal>
        <BaseDialog.Backdrop
          className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        />
        <BaseDialog.Popup
          className={cn(
            "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50",
            "w-[min(92vw,420px)] rounded-lg border border-border bg-surface p-5 shadow-xl",
          )}
        >
          {title ? (
            <BaseDialog.Title className="text-base font-semibold text-text mb-2">
              {title}
            </BaseDialog.Title>
          ) : null}

          {children}

          <BaseDialog.Close className="mt-4 text-sm text-muted hover:text-text">
            关闭
          </BaseDialog.Close>
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}
