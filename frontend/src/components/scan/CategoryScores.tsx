import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { scoreTone } from "@/lib/format";
import type { Category } from "@/lib/types";
import { CATEGORY_LABELS } from "@/lib/types";

interface CategoryScoresProps {
  scores: Partial<Record<Category, number | null>> | Record<string, number | null>;
}

export function CategoryScores({ scores }: CategoryScoresProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {(Object.entries(CATEGORY_LABELS) as [Category, string][]).map(([key, label]) => {
        const score = scores[key];
        const tone = scoreTone(score);
        return (
          <Card key={key}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">{label}</span>
                <span className={cn("text-sm font-semibold", tone.text)}>
                  {score === null || score === undefined ? "—" : Math.round(score)}
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={cn("h-full rounded-full transition-all duration-700", tone.bar)}
                  style={{
                    width: `${score === null || score === undefined ? 0 : Math.max(0, Math.min(100, score))}%`,
                  }}
                />
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
