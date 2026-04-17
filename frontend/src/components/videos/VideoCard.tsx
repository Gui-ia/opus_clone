import { Link } from 'react-router-dom';
import { Play, Eye, Clock } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';
import { formatDuration, formatNumber, formatRelativeTime, getYouTubeThumbnail } from '../../lib/utils';
import type { SourceVideoResponse } from '../../types/video';

interface Props {
  video: SourceVideoResponse;
}

export function VideoCard({ video }: Props) {
  const isYouTube = video.url?.includes('youtube.com') || video.url?.includes('youtu.be');
  const thumbnail = isYouTube ? getYouTubeThumbnail(video.external_id) : null;

  return (
    <Link
      to={`/videos/${video.id}`}
      className="group flex gap-4 rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-700"
    >
      {/* Thumbnail */}
      <div className="relative h-20 w-36 flex-shrink-0 overflow-hidden rounded-lg bg-gray-800">
        {thumbnail ? (
          <img
            src={thumbnail}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Play className="h-8 w-8 text-gray-600" />
          </div>
        )}
        {video.duration_s && (
          <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-medium">
            {formatDuration(video.duration_s)}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-medium group-hover:text-white">
          {video.title || 'Sem titulo'}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
          {video.view_count !== null && (
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              {formatNumber(video.view_count)}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatRelativeTime(video.discovered_at)}
          </span>
        </div>
        <div className="mt-2">
          <StatusBadge type="video" status={video.status} />
        </div>
      </div>
    </Link>
  );
}
