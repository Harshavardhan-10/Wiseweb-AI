import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Variant = "error" | "warning" | "info" | "success";

const styles: Record<Variant, string> = {
  error: "border-red-200 bg-red-50 text-red-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  info: "border-sky-200 bg-sky-50 text-sky-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  title?: string;
}

export function Alert({ className, variant = "info", title, children, ...props }: AlertProps) {
  return (
    <div
      className={cn("rounded-md border px-4 py-3 text-sm", styles[variant], className)}
      {...props}
    >
      {title && <p className="mb-1 font-semibold">{title}</p>}
      {children}
    </div>
  );
}
