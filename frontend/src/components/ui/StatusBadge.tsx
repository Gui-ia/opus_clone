import type { VideoStatus } from '../../types/video';
import type { ClipStatus } from '../../types/clip';

const VIDEO_STATUS_CONFIG: Record<VideoStatus, { label: string; className: string }> = {
  discovered:    { label: 'Descoberto',       className: 'bg-slate-500/20 text-slate-300' },
  downloading:   { label: 'Baixando',         className: 'bg-blue-500/20 text-blue-300 animate-pulse' },
  downloaded:    { label: 'Baixado',          className: 'bg-blue-600/20 text-blue-300' },
  transcribing:  { label: 'Transcrevendo',    className: 'bg-violet-500/20 text-violet-300 animate-pulse' },
  analyzing:     { label: 'Analisando',       className: 'bg-amber-500/20 text-amber-300 animate-pulse' },
  scoring:       { label: 'Pontuando',        className: 'bg-amber-600/20 text-amber-300 animate-pulse' },
  ready_to_clip: { label: 'Pronto p/ Cortar', className: 'bg-cyan-500/20 text-cyan-300' },
  clipping:      { label: 'Cortando',         className: 'bg-purple-500/20 text-purple-300 animate-pulse' },
  completed:     { label: 'Concluido',        className: 'bg-green-500/20 text-green-300' },
  failed:        { label: 'Falhou',           className: 'bg-red-500/20 text-red-300' },
  skipped:       { label: 'Ignorado',         className: 'bg-gray-500/20 text-gray-400' },
};

const CLIP_STATUS_CONFIG: Record<ClipStatus, { label: string; className: string }> = {
  planned:    { label: 'Planejado',    className: 'bg-slate-500/20 text-slate-300' },
  rendering:  { label: 'Renderizando', className: 'bg-blue-500/20 text-blue-300 animate-pulse' },
  ready:      { label: 'Pronto',       className: 'bg-cyan-500/20 text-cyan-300' },
  approved:   { label: 'Aprovado',     className: 'bg-green-500/20 text-green-300' },
  rejected:   { label: 'Rejeitado',    className: 'bg-red-400/20 text-red-300' },
  publishing: { label: 'Publicando',   className: 'bg-amber-500/20 text-amber-300 animate-pulse' },
  published:  { label: 'Publicado',    className: 'bg-green-600/20 text-green-200' },
  failed:     { label: 'Falhou',       className: 'bg-red-500/20 text-red-300' },
};

type Props =
  | { type: 'video'; status: VideoStatus }
  | { type: 'clip'; status: ClipStatus };

export function StatusBadge(props: Props) {
  const config =
    props.type === 'video'
      ? VIDEO_STATUS_CONFIG[props.status]
      : CLIP_STATUS_CONFIG[props.status];

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
