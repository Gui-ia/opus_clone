import { StatusBadge } from '../ui/StatusBadge';
import { formatRelativeTime } from '../../lib/utils';
import type { SourceVideoResponse, VideoStatus } from '../../types/video';
import type { ClipResponse, ClipStatus } from '../../types/clip';

interface VideoItem {
  id: string;
  type: 'video';
  title: string;
  status: VideoStatus;
  time: string;
}

interface ClipItem {
  id: string;
  type: 'clip';
  title: string;
  status: ClipStatus;
  time: string;
}

type ActivityItem = VideoItem | ClipItem;

interface Props {
  videos: SourceVideoResponse[];
  clips: ClipResponse[];
}

export function ActivityFeed({ videos, clips }: Props) {
  const items: ActivityItem[] = [
    ...videos.map((v): VideoItem => ({
      id: v.id,
      type: 'video',
      title: v.title || 'Sem titulo',
      status: v.status,
      time: v.discovered_at,
    })),
    ...clips.map((c): ClipItem => ({
      id: c.id,
      type: 'clip',
      title: c.title_suggestion || c.hook_text || 'Clip',
      status: c.status,
      time: c.created_at,
    })),
  ];

  items.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
  const display = items.slice(0, 10);

  if (display.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-500">Sem atividade recente</p>;
  }

  return (
    <div className="space-y-2">
      {display.map((item) => (
        <div
          key={item.id}
          className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-3"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm">{item.title}</p>
            <p className="text-xs text-gray-500">{formatRelativeTime(item.time)}</p>
          </div>
          {item.type === 'video' ? (
            <StatusBadge type="video" status={item.status} />
          ) : (
            <StatusBadge type="clip" status={item.status} />
          )}
        </div>
      ))}
    </div>
  );
}
