import { useNavigate } from 'react-router-dom';
import { Pencil, Trash2 } from 'lucide-react';
import { PlatformIcon } from '../ui/PlatformIcon';
import { formatRelativeTime } from '../../lib/utils';
import type { ChannelResponse } from '../../types/channel';

interface Props {
  channel: ChannelResponse;
  onEdit: (channel: ChannelResponse) => void;
  onDelete: (channel: ChannelResponse) => void;
}

export function ChannelCard({ channel, onEdit, onDelete }: Props) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/canais/${channel.id}`)}
      className="cursor-pointer rounded-xl border border-gray-800 bg-gray-900 p-5 transition-colors hover:border-violet-500/50"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <PlatformIcon platform={channel.platform} size={24} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-medium">
                {channel.display_name || channel.username}
              </h3>
              <div
                className={`h-2 w-2 rounded-full ${
                  channel.is_active ? 'bg-green-400' : 'bg-gray-600'
                }`}
                title={channel.is_active ? 'Ativo' : 'Inativo'}
              />
            </div>
            <p className="text-sm text-gray-500">@{channel.username}</p>
          </div>
        </div>
        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onEdit(channel)}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-800 hover:text-gray-300"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(channel)}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-800 hover:text-red-400"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-xs text-gray-500">
        <span>Score min: {channel.min_viral_score}</span>
        <span>Max clips: {channel.max_clips_per_video}</span>
        <span>Preset: {channel.style_preset}</span>
      </div>

      {channel.last_polled_at && (
        <p className="mt-3 text-xs text-gray-600">
          Ultimo poll: {formatRelativeTime(channel.last_polled_at)}
        </p>
      )}
    </div>
  );
}
