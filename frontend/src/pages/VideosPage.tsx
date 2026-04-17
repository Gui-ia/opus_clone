import { useState, useMemo } from 'react';
import { VideoCard } from '../components/videos/VideoCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Pagination } from '../components/ui/Pagination';
import { useVideos } from '../hooks/useVideos';
import { useChannels } from '../hooks/useChannels';
import { usePagination } from '../hooks/usePagination';
import { TRANSIENT_VIDEO_STATUSES } from '../types/video';
import type { VideoStatus } from '../types/video';

const STATUS_OPTIONS: { value: '' | VideoStatus; label: string }[] = [
  { value: '', label: 'Todos os status' },
  { value: 'discovered', label: 'Descoberto' },
  { value: 'downloading', label: 'Baixando' },
  { value: 'downloaded', label: 'Baixado' },
  { value: 'transcribing', label: 'Transcrevendo' },
  { value: 'analyzing', label: 'Analisando' },
  { value: 'scoring', label: 'Pontuando' },
  { value: 'ready_to_clip', label: 'Pronto p/ Cortar' },
  { value: 'clipping', label: 'Cortando' },
  { value: 'completed', label: 'Concluido' },
  { value: 'failed', label: 'Falhou' },
  { value: 'skipped', label: 'Ignorado' },
];

export function VideosPage() {
  const { page, pageSize, setPage } = usePagination();
  const [channelFilter, setChannelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<'' | VideoStatus>('');

  const { data: channels } = useChannels({ page_size: 100 });

  // Determine polling interval: faster when filtering for transient statuses
  const refetchInterval = useMemo(() => {
    if (statusFilter && TRANSIENT_VIDEO_STATUSES.includes(statusFilter as VideoStatus)) {
      return 10_000;
    }
    return 30_000;
  }, [statusFilter]);

  const { data: videos, isLoading } = useVideos(
    {
      channel_id: channelFilter || undefined,
      status: statusFilter || undefined,
      page,
      page_size: pageSize,
    },
    { refetchInterval },
  );

  const selectClass =
    'rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300';

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Videos</h1>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={channelFilter}
          onChange={(e) => {
            setChannelFilter(e.target.value);
            setPage(1);
          }}
          className={selectClass}
        >
          <option value="">Todos os canais</option>
          {channels?.map((ch) => (
            <option key={ch.id} value={ch.id}>
              {ch.display_name || ch.username}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as '' | VideoStatus);
            setPage(1);
          }}
          className={selectClass}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : !videos || videos.length === 0 ? (
        <EmptyState message="Nenhum video encontrado" />
      ) : (
        <>
          <div className="space-y-3">
            {videos.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
          <div className="mt-4">
            <Pagination
              page={page}
              pageSize={pageSize}
              itemCount={videos.length}
              onPageChange={setPage}
            />
          </div>
        </>
      )}
    </div>
  );
}
