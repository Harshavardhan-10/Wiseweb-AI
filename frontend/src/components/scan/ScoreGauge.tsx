import { cn } from "@/lib/utils";
import { scoreTone } from "@/lib/format";

interface ScoreGaugeProps {
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
  label?: string;
}

const sizes = {
  sm: { diameter: 72, stroke: 7, text: "text-lg", label: "text-[8px]", pad: "p-1.5" },
  md: { diameter: 110, stroke: 9, text: "text-2xl", label: "text-[10px]", pad: "p-2.5" },
  lg: { diameter: 150, stroke: 11, text: "text-3xl", label: "text-xs", pad: "p-3.5" },
};

export function ScoreGauge({ score, size = "md", label }: ScoreGaugeProps) {
  const { diameter, stroke, text, label: labelClass, pad } = sizes[size];
  const tone = scoreTone(score);
  const radius = (diameter - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const value = score === null || score === undefined ? 0 : Math.max(0, Math.min(100, score));
  const dash = (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: diameter, height: diameter }}>
        <svg width={diameter} height={diameter} className="-rotate-90">
          <circle
            cx={diameter / 2}
            cy={diameter / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            className="text-slate-100"
          />
          {score !== null && score !== undefined && (
            <circle
              cx={diameter / 2}
              cy={diameter / 2}
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circumference}`}
              className={cn("transition-all duration-700", tone.bar)}
            />
          )}
        </svg>
        <div className={cn("absolute inset-0 flex flex-col items-center justify-center", pad)}>
          <span className={cn("font-bold leading-none", text, tone.text)}>
            {score === null || score === undefined ? "—" : Math.round(score)}
          </span>
          <span
            className={cn(
              "mt-1 text-center font-medium uppercase leading-none tracking-wide text-slate-400",
              labelClass,
            )}
          >
            {tone.label}
          </span>
        </div>
      </div>
      {label && <p className="text-xs font-medium text-slate-600">{label}</p>}
    </div>
  );
}
