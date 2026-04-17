import { Scissors } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';
import { ScoreGauge } from '../ui/ScoreGauge';
import type { ClipResponse } from '../../types/clip';

interface Props {
  clip: ClipResponse;
  selected?: boolean;
  onSelect?: (id: string) => void;
  onClick: (clip: ClipResponse) => void;
}

export function ClipCard({ clip, selected, onSelect, onClick }: Props) {
  const durationSec = Math.round((clip.end_ms - clip.start_ms) / 1000);

  return (
    <div
      className={`group cursor-pointer rounded-xl border bg-gray-900 p-4 transition-colors hover:border-gray-600 ${
        selected ? 'border-violet-500' : 'border-gray-800'
      }`}
      onClick={() => onClick(clip)}
    >
      {/* Top row: checkbox + score */}
      <div className="flex items-start justify-between">
        {onSelect && (
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(clip.id);
            }}
            onClick={(e) => e.stopPropagation()}
            className="mt-1 h-4 w-4 rounded border-gray-600 bg-gray-800 accent-violet-500"
          />
        )}
        <ScoreGauge score={clip.viral_score} size="md" />
      </div>

      {/* Thumbnail placeholder */}
      <div className="mt-3 flex h-24 items-center justify-center rounded-lg bg-gray-800">
        {clip.thumbnail_url ? (
          <img
            src={clip.thumbnail_url}
            alt=""
            className="h-full w-full rounded-lg object-cover"
          />
        ) : (
          <Scissors className="h-8 w-8 text-gray-600" />
        )}
      </div>

      {/* Info */}
      <div className="mt-3">
        <p className="line-clamp-2 text-sm font-medium">
          {clip.hook_text || clip.title_suggestion || 'Sem titulo'}
        </p>
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-gray-500">{durationSec}s</span>
          {clip.category && (
            <span className="rounded-full bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400">
              {clip.category}
            </span>
          )}
        </div>
        <div className="mt-2">
          <StatusBadge type="clip" status={clip.status} />
        </div>
      </div>
    </div>
  );
}
