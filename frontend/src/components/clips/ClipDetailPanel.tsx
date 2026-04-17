import { X, Clock, Hash, Sparkles, Target } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';
import { ScoreGauge } from '../ui/ScoreGauge';
import { ClipApprovalForm } from './ClipApprovalForm';
import { formatDurationMs, formatRelativeTime } from '../../lib/utils';
import type { ClipResponse, ClipApproval } from '../../types/clip';

interface Props {
  clip: ClipResponse;
  onClose: () => void;
  onApprove: (id: string, data?: ClipApproval) => void;
  onReject: (id: string) => void;
  loading?: boolean;
}

export function ClipDetailPanel({
  clip,
  onClose,
  onApprove,
  onReject,
  loading,
}: Props) {
  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-gray-800 bg-gray-900 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 px-5 py-4">
        <h2 className="font-semibold">Detalhes do Clip</h2>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-gray-400 hover:bg-gray-800 hover:text-gray-200"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {/* Video Player */}
        {clip.minio_key && (
          <div className="mb-5 overflow-hidden rounded-lg bg-black">
            <video
              controls
              className="w-full"
              src={`/api/clips/${clip.id}/stream`}
              preload="metadata"
            />
          </div>
        )}

        {/* Score + Status */}
        <div className="flex items-center justify-between">
          <ScoreGauge score={clip.viral_score} size="lg" />
          <div className="text-right">
            <StatusBadge type="clip" status={clip.status} />
            {clip.confidence !== null && (
              <p className="mt-1 text-xs text-gray-500">
                Confianca: {Math.round((clip.confidence ?? 0) * 100)}%
              </p>
            )}
          </div>
        </div>

        {/* Title */}
        <div className="mt-5">
          <h3 className="text-lg font-medium">
            {clip.title_suggestion || 'Sem titulo'}
          </h3>
        </div>

        {/* Hook */}
        {clip.hook_text && (
          <div className="mt-4 rounded-lg border border-gray-800 bg-gray-800/50 p-3">
            <p className="mb-1 text-xs font-medium text-gray-400">
              <Sparkles className="mr-1 inline h-3 w-3" />
              Hook
            </p>
            <p className="text-sm italic text-gray-300">"{clip.hook_text}"</p>
          </div>
        )}

        {/* Metadata */}
        <div className="mt-4 space-y-2.5">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Clock className="h-4 w-4" />
            <span>
              {formatDurationMs(clip.start_ms)} - {formatDurationMs(clip.end_ms)}
              <span className="ml-2 text-gray-600">
                ({Math.round((clip.end_ms - clip.start_ms) / 1000)}s)
              </span>
            </span>
          </div>

          {clip.hook_type && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Target className="h-4 w-4" />
              <span>Tipo: {clip.hook_type}</span>
            </div>
          )}

          {clip.category && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Hash className="h-4 w-4" />
              <span>Categoria: {clip.category}</span>
            </div>
          )}
        </div>

        {/* Hashtags */}
        {clip.hashtags && clip.hashtags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {clip.hashtags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs text-violet-300"
              >
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        )}

        {/* Rationale */}
        {clip.rationale && (
          <div className="mt-4">
            <p className="mb-1 text-xs font-medium text-gray-400">Justificativa</p>
            <p className="text-sm text-gray-400">{clip.rationale}</p>
          </div>
        )}

        {/* Timestamps */}
        <div className="mt-4 space-y-1 text-xs text-gray-600">
          <p>Criado: {formatRelativeTime(clip.created_at)}</p>
          {clip.rendered_at && <p>Renderizado: {formatRelativeTime(clip.rendered_at)}</p>}
          {clip.approved_at && <p>Aprovado: {formatRelativeTime(clip.approved_at)}</p>}
        </div>

        {/* Approval form - only for clips in ready or rejected status */}
        {(clip.status === 'ready' || clip.status === 'rejected') && (
          <div className="mt-6">
            <ClipApprovalForm
              clip={clip}
              onApprove={(data) => onApprove(clip.id, data)}
              onReject={() => onReject(clip.id)}
              loading={loading}
            />
          </div>
        )}
      </div>
    </div>
  );
}
