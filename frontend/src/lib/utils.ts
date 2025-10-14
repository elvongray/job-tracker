import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, isPast } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatReviewTime(isoDateString: string): string {
  const date = new Date(isoDateString);

  // Check if the review time has already passed
  if (isPast(date)) {
    return "Ready for review";
  }

  // Formats the date to the user's local timezone, e.g., "Aug 18, 2025, 5:45 PM"
  return format(date, "MMM d, yyyy, p");
}
