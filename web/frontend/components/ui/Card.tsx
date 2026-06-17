import type { HTMLAttributes } from "react";
import { cn } from "./cn";
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-surface p-5", className)} {...props} />;
}
