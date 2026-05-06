// Tremor cx [v0.0.0] - uses project's existing clsx + tailwind-merge
import clsx, { type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cx(...args: ClassValue[]) {
  return twMerge(clsx(...args))
}
