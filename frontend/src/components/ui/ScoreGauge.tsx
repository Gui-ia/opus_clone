import { clsx } from 'clsx';

function getScoreColor(score: number) {
  if (score >= 80) return 'text-green-400';
  if (score >= 65) return 'text-emerald-400';
  if (score >= 40) return 'text-amber-400';
  return 'text-red-400';
}

function getScoreBg(score: number) {
  if (score >= 80) return 'bg-green-400';
  if (score >= 65) return 'bg-emerald-400';
  if (score >= 40) return 'bg-amber-400';
  return 'bg-red-400';
}

export function ScoreGauge({
  score,
  size = 'md',
}: {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
}) {
  if (score === null) {
    return (
      <span className="text-xs text-gray-500">N/A</span>
    );
  }

  const dims = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-12 w-12 text-sm',
    lg: 'h-16 w-16 text-lg',
  };

  const radius = size === 'sm' ? 12 : size === 'md' ? 18 : 24;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const viewBox = size === 'sm' ? 32 : size === 'md' ? 48 : 64;
  const center = viewBox / 2;
  const strokeWidth = size === 'sm' ? 3 : 4;

  return (
    <div className={clsx('relative inline-flex items-center justify-center', dims[size])}>
      <svg
        className="absolute inset-0 -rotate-90"
        viewBox={`0 0 ${viewBox} ${viewBox}`}
      >
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-800"
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          className={getScoreColor(score)}
        />
      </svg>
      <span className={clsx('relative font-bold', getScoreColor(score))}>
        {Math.round(score)}
      </span>
    </div>
  );
}

export function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return null;

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-gray-800">
        <div
          className={clsx('h-full rounded-full transition-all', getScoreBg(score))}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
      <span className={clsx('text-xs font-medium', getScoreColor(score))}>
        {Math.round(score)}
      </span>
    </div>
  );
}
