import { Check, Loader2, AlertCircle, Circle } from 'lucide-react';
import type { VideoStatus } from '../../types/video';
import { VIDEO_STATUS_ORDER, TRANSIENT_VIDEO_STATUSES } from '../../types/video';

const STEP_LABELS: Record<string, string> = {
  discovered: 'Descoberto',
  downloading: 'Baixando',
  downloaded: 'Baixado',
  transcribing: 'Transcrevendo',
  analyzing: 'Analisando',
  scoring: 'Pontuando',
  ready_to_clip: 'Pronto p/ Cortar',
  clipping: 'Cortando',
  completed: 'Concluido',
};

interface Props {
  status: VideoStatus;
  errorMessage?: string | null;
}

export function VideoStatusTimeline({ status, errorMessage }: Props) {
  const currentIndex = VIDEO_STATUS_ORDER.indexOf(status);
  const isFailed = status === 'failed';
  const isSkipped = status === 'skipped';

  return (
    <div className="space-y-0">
      {VIDEO_STATUS_ORDER.map((step, idx) => {
        const isCompleted = !isFailed && !isSkipped && idx < currentIndex;
        const isCurrent = step === status;
        const isActive = isCurrent && TRANSIENT_VIDEO_STATUSES.includes(step);

        return (
          <div key={step} className="flex items-start gap-3">
            {/* Icon */}
            <div className="flex flex-col items-center">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  isFailed && isCurrent
                    ? 'bg-red-500/20 text-red-400'
                    : isCompleted
                      ? 'bg-green-500/20 text-green-400'
                      : isActive
                        ? 'bg-violet-500/20 text-violet-400'
                        : isCurrent
                          ? 'bg-cyan-500/20 text-cyan-400'
                          : 'bg-gray-800 text-gray-600'
                }`}
              >
                {isFailed && isCurrent ? (
                  <AlertCircle className="h-3.5 w-3.5" />
                ) : isCompleted ? (
                  <Check className="h-3.5 w-3.5" />
                ) : isActive ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Circle className="h-2.5 w-2.5" />
                )}
              </div>
              {idx < VIDEO_STATUS_ORDER.length - 1 && (
                <div
                  className={`h-6 w-px ${
                    isCompleted ? 'bg-green-500/30' : 'bg-gray-800'
                  }`}
                />
              )}
            </div>

            {/* Label */}
            <div className="pb-6">
              <span
                className={`text-sm ${
                  isFailed && isCurrent
                    ? 'font-medium text-red-400'
                    : isCompleted
                      ? 'text-gray-400'
                      : isCurrent
                        ? 'font-medium text-white'
                        : 'text-gray-600'
                }`}
              >
                {STEP_LABELS[step]}
              </span>
              {isFailed && isCurrent && errorMessage && (
                <p className="mt-1 text-xs text-red-400/70">{errorMessage}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
