import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Eye, Clock } from 'lucide-react';
import { VideoStatusTimeline } from '../components/videos/VideoStatusTimeline';
import { ClipCard } from '../components/clips/ClipCard';
import { ClipDetailPanel } from '../components/clips/ClipDetailPanel';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useVideo } from '../hooks/useVideos';
import { useClips, useApproveClip, useRejectClip } from '../hooks/useClips';
import { formatDuration, formatNumber, formatRelativeTime, getYouTubeThumbnail } from '../lib/utils';
import { TRANSIENT_VIDEO_STATUSES } from '../types/video';
import type { ClipResponse, ClipApproval } from '../types/clip';
import { useState } from 'react';

export function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [selectedClip, setSelectedClip] = useState<ClipResponse | null>(null);

  const { data: video, isLoading: loadingVideo } = useVideo(id!);
  const { data: clips } = useClips(
    { source_video_id: id, page_size: 50 },
    {
      refetchInterval: video && TRANSIENT_VIDEO_STATUSES.includes(video.status)
        ? 10_000
        : 30_000,
    },
  );

  const approveMutation = useApproveClip();
  const rejectMutation = useRejectClip();

  if (loadingVideo) return <LoadingSpinner />;
  if (!video) return <EmptyState message="Video nao encontrado" />;

  const isYouTube = video.url?.includes('youtube.com') || video.url?.includes('youtu.be');
  const thumbnail = isYouTube ? getYouTubeThumbnail(video.external_id) : null;

  const handleApprove = (clipId: string, data?: ClipApproval) => {
    approveMutation.mutate({ id: clipId, data });
    setSelectedClip(null);
  };

  const handleReject = (clipId: string) => {
    rejectMutation.mutate(clipId);
    setSelectedClip(null);
  };

  return (
    <div>
      {/* Back */}
      <Link
        to="/videos"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar para videos
      </Link>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Video info */}
        <div className="lg:col-span-2">
          {/* Thumbnail */}
          {thumbnail && (
            <div className="mb-4 overflow-hidden rounded-xl">
              <img src={thumbnail} alt="" className="w-full" />
            </div>
          )}

          {/* Title + metadata */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold">
                {video.title || 'Sem titulo'}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-gray-400">
                {video.duration_s && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {formatDuration(video.duration_s)}
                  </span>
                )}
                {video.view_count !== null && (
                  <span className="flex items-center gap-1">
                    <Eye className="h-4 w-4" />
                    {formatNumber(video.view_count)} views
                  </span>
                )}
                <span>Descoberto {formatRelativeTime(video.discovered_at)}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge type="video" status={video.status} />
              {video.url && (
                <a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg p-2 text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>

          {/* Status Timeline */}
          <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-5">
            <h2 className="mb-4 text-sm font-semibold text-gray-300">
              Progresso do Processamento
            </h2>
            <VideoStatusTimeline
              status={video.status}
              errorMessage={video.error_message}
            />
          </div>
        </div>

        {/* Right: Clips */}
        <div>
          <h2 className="mb-4 text-lg font-semibold">
            Clips Gerados ({clips?.length ?? 0})
          </h2>
          {!clips || clips.length === 0 ? (
            <EmptyState message="Nenhum clip gerado ainda" />
          ) : (
            <div className="space-y-3">
              {clips.map((clip) => (
                <ClipCard
                  key={clip.id}
                  clip={clip}
                  onClick={setSelectedClip}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Clip detail panel */}
      {selectedClip && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/50"
            onClick={() => setSelectedClip(null)}
          />
          <ClipDetailPanel
            clip={selectedClip}
            onClose={() => setSelectedClip(null)}
            onApprove={handleApprove}
            onReject={handleReject}
            loading={approveMutation.isPending || rejectMutation.isPending}
          />
        </>
      )}
    </div>
  );
}
