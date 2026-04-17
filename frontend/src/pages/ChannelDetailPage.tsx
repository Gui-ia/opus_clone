import { useState, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Play,
  Eye,
  Clock,
  Square,
  CheckSquare,
  Pencil,
  Trash2,
  Power,
  Search,
  Filter,
} from 'lucide-react';
import {
  useChannel,
  useUpdateChannel,
  useDeleteChannel,
  useFetchChannelVideos,
} from '../hooks/useChannels';
import { useVideos, useProcessVideos, useDeleteVideos } from '../hooks/useVideos';
import { ChannelForm } from '../components/channels/ChannelForm';
import { Modal } from '../components/ui/Modal';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { PlatformIcon } from '../components/ui/PlatformIcon';
import { StatusBadge } from '../components/ui/StatusBadge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import {
  formatDuration,
  formatNumber,
  formatRelativeTime,
  getYouTubeThumbnail,
} from '../lib/utils';
import type { ChannelUpdate } from '../types/channel';
import type { SourceVideoResponse } from '../types/video';

export function ChannelDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: channel, isLoading: channelLoading } = useChannel(id!);
  const { data: videos, isLoading: videosLoading } = useVideos(
    { channel_id: id, page_size: 100 },
    { refetchInterval: 15_000 },
  );

  const fetchMutation = useFetchChannelVideos();
  const processMutation = useProcessVideos();
  const deleteVideosMutation = useDeleteVideos();
  const updateMutation = useUpdateChannel();
  const deleteMutation = useDeleteChannel();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [minDuration, setMinDuration] = useState<number>(0);
  const [sortBy, setSortBy] = useState<'recent' | 'views'>('recent');

  const discoveredVideos = useMemo(() => {
    let list = videos?.filter((v) => v.status === 'discovered') ?? [];

    // Filter by search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter((v) => v.title?.toLowerCase().includes(q));
    }

    // Filter by min duration
    if (minDuration > 0) {
      list = list.filter((v) => (v.duration_s ?? 0) >= minDuration);
    }

    // Sort
    if (sortBy === 'views') {
      list = [...list].sort((a, b) => (b.view_count ?? 0) - (a.view_count ?? 0));
    } else {
      list = [...list].sort((a, b) => {
        const da = a.published_at ?? a.discovered_at;
        const db = b.published_at ?? b.discovered_at;
        return new Date(db).getTime() - new Date(da).getTime();
      });
    }

    return list;
  }, [videos, searchQuery, minDuration, sortBy]);

  const processingOrDoneVideos = useMemo(
    () => videos?.filter((v) => v.status !== 'discovered') ?? [],
    [videos],
  );

  const toggleSelect = (videoId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) next.delete(videoId);
      else next.add(videoId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    const filteredIds = discoveredVideos.map((v) => v.id);
    const allSelected = filteredIds.length > 0 && filteredIds.every((id) => selected.has(id));
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filteredIds));
    }
  };

  const allFilteredSelected =
    discoveredVideos.length > 0 &&
    discoveredVideos.every((v) => selected.has(v.id));

  const handleFetch = () => {
    if (!id) return;
    fetchMutation.mutate(id);
  };

  const handleProcess = () => {
    if (selected.size === 0) return;
    processMutation.mutate([...selected], {
      onSuccess: () => setSelected(new Set()),
    });
  };

  const handleDeleteVideos = () => {
    if (selected.size === 0) return;
    deleteVideosMutation.mutate([...selected], {
      onSuccess: () => setSelected(new Set()),
    });
  };

  const handleEdit = (data: ChannelUpdate) => {
    if (!id) return;
    updateMutation.mutate(
      { id, data },
      { onSuccess: () => setShowEditModal(false) },
    );
  };

  const handleDelete = () => {
    if (!id) return;
    deleteMutation.mutate(id, {
      onSuccess: () => navigate('/canais'),
    });
  };

  const handleToggleActive = () => {
    if (!id || !channel) return;
    updateMutation.mutate({ id, data: { is_active: !channel.is_active } });
  };

  if (channelLoading) return <LoadingSpinner />;
  if (!channel) return <EmptyState message="Canal nao encontrado" />;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/canais"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para Canais
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <PlatformIcon platform={channel.platform} size={32} />
            <div>
              <h1 className="text-2xl font-bold">
                {channel.display_name || channel.username}
              </h1>
              <p className="text-sm text-gray-500">@{channel.username}</p>
            </div>
            <div
              className={`h-2.5 w-2.5 rounded-full ${
                channel.is_active ? 'bg-green-400' : 'bg-gray-600'
              }`}
              title={channel.is_active ? 'Ativo' : 'Inativo'}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleToggleActive}
              disabled={updateMutation.isPending}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                channel.is_active
                  ? 'text-yellow-400 hover:bg-yellow-500/10'
                  : 'text-green-400 hover:bg-green-500/10'
              }`}
              title={channel.is_active ? 'Desativar' : 'Ativar'}
            >
              <Power className="h-4 w-4" />
              {channel.is_active ? 'Desativar' : 'Ativar'}
            </button>
            <button
              onClick={() => setShowEditModal(true)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
            >
              <Pencil className="h-4 w-4" />
              Editar
            </button>
            <button
              onClick={() => setShowDeleteDialog(true)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10"
            >
              <Trash2 className="h-4 w-4" />
              Excluir
            </button>
            <button
              onClick={handleFetch}
              disabled={fetchMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${fetchMutation.isPending ? 'animate-spin' : ''}`}
              />
              {fetchMutation.isPending ? 'Buscando...' : 'Buscar Videos'}
            </button>
          </div>
        </div>

        {/* Channel stats */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-500">
          <span>Plataforma: {channel.platform}</span>
          <span>ID: {channel.external_id}</span>
          <span>Score min: {channel.min_viral_score}</span>
          <span>Max clips: {channel.max_clips_per_video}</span>
          <span>Preset: {channel.style_preset}</span>
          <span>Poll: {channel.poll_interval_seconds}s</span>
          {channel.last_polled_at && (
            <span>Ultimo poll: {formatRelativeTime(channel.last_polled_at)}</span>
          )}
        </div>
      </div>

      {/* Discovered videos - selectable */}
      {(videos?.some((v) => v.status === 'discovered') ?? false) && (
        <section className="mb-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Videos Disponiveis ({discoveredVideos.length})
            </h2>
            <div className="flex items-center gap-3">
              <button
                onClick={toggleSelectAll}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
              >
                {allFilteredSelected ? (
                  <CheckSquare className="h-4 w-4" />
                ) : (
                  <Square className="h-4 w-4" />
                )}
                {allFilteredSelected ? 'Desmarcar Todos' : 'Selecionar Todos'}
              </button>
              <button
                onClick={handleDeleteVideos}
                disabled={selected.size === 0 || deleteVideosMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                {deleteVideosMutation.isPending
                  ? 'Excluindo...'
                  : `Excluir (${selected.size})`}
              </button>
              <button
                onClick={handleProcess}
                disabled={selected.size === 0 || processMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                {processMutation.isPending
                  ? 'Processando...'
                  : `Processar Selecionados (${selected.size})`}
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar por titulo..."
                className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-9 pr-3 text-sm text-gray-100 placeholder-gray-500 focus:border-violet-500 focus:outline-none"
              />
            </div>
            <select
              value={minDuration}
              onChange={(e) => setMinDuration(Number(e.target.value))}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300"
            >
              <option value={0}>Qualquer duracao</option>
              <option value={180}>+ de 3 min</option>
              <option value={300}>+ de 5 min</option>
              <option value={600}>+ de 10 min</option>
              <option value={1200}>+ de 20 min</option>
              <option value={1800}>+ de 30 min</option>
              <option value={3600}>+ de 1 hora</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'recent' | 'views')}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300"
            >
              <option value="recent">Mais recente</option>
              <option value="views">Mais views</option>
            </select>
          </div>

          {discoveredVideos.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">
              Nenhum video corresponde aos filtros
            </p>
          ) : (
            <div className="space-y-2">
              {discoveredVideos.map((video) => (
                <VideoSelectableRow
                  key={video.id}
                  video={video}
                  selected={selected.has(video.id)}
                  onToggle={() => toggleSelect(video.id)}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* No videos at all */}
      {!videosLoading && (!videos || videos.length === 0) && (
        <EmptyState message="Nenhum video encontrado. Clique em 'Buscar Videos' para puxar do canal." />
      )}

      {/* Processing/completed videos */}
      {processingOrDoneVideos.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">
            Videos em Processamento / Concluidos ({processingOrDoneVideos.length})
          </h2>

          <div className="space-y-2">
            {processingOrDoneVideos.map((video) => (
              <VideoRow key={video.id} video={video} />
            ))}
          </div>
        </section>
      )}

      {/* Edit modal */}
      <Modal
        open={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Editar Canal"
      >
        <ChannelForm
          channel={channel}
          onSubmit={(data) => handleEdit(data as ChannelUpdate)}
          onCancel={() => setShowEditModal(false)}
          loading={updateMutation.isPending}
        />
      </Modal>

      {/* Delete confirm */}
      <ConfirmDialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        onConfirm={handleDelete}
        title="Desativar Canal"
        message={`Tem certeza que deseja desativar o canal "${channel.display_name || channel.username}"?`}
        confirmLabel="Desativar"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

function VideoSelectableRow({
  video,
  selected,
  onToggle,
}: {
  video: SourceVideoResponse;
  selected: boolean;
  onToggle: () => void;
}) {
  const isYouTube =
    video.url?.includes('youtube.com') || video.url?.includes('youtu.be');
  const thumbnail = isYouTube
    ? getYouTubeThumbnail(video.external_id)
    : null;

  return (
    <div
      onClick={onToggle}
      className={`flex cursor-pointer items-center gap-4 rounded-xl border p-4 transition-colors ${
        selected
          ? 'border-violet-500 bg-violet-500/10'
          : 'border-gray-800 bg-gray-900 hover:border-gray-700'
      }`}
    >
      {/* Checkbox */}
      <div className="flex-shrink-0">
        {selected ? (
          <CheckSquare className="h-5 w-5 text-violet-400" />
        ) : (
          <Square className="h-5 w-5 text-gray-600" />
        )}
      </div>

      {/* Thumbnail */}
      <div className="relative h-16 w-28 flex-shrink-0 overflow-hidden rounded-lg bg-gray-800">
        {thumbnail ? (
          <img
            src={thumbnail}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Play className="h-6 w-6 text-gray-600" />
          </div>
        )}
        {video.duration_s && (
          <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1 py-0.5 text-[10px] font-medium">
            {formatDuration(video.duration_s)}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-medium">
          {video.title || 'Sem titulo'}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
          {video.view_count !== null && (
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              {formatNumber(video.view_count)}
            </span>
          )}
          {video.published_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(video.published_at)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function VideoRow({ video }: { video: SourceVideoResponse }) {
  const isYouTube =
    video.url?.includes('youtube.com') || video.url?.includes('youtu.be');
  const thumbnail = isYouTube
    ? getYouTubeThumbnail(video.external_id)
    : null;

  return (
    <Link
      to={`/videos/${video.id}`}
      className="group flex items-center gap-4 rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-700"
    >
      {/* Thumbnail */}
      <div className="relative h-16 w-28 flex-shrink-0 overflow-hidden rounded-lg bg-gray-800">
        {thumbnail ? (
          <img
            src={thumbnail}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Play className="h-6 w-6 text-gray-600" />
          </div>
        )}
        {video.duration_s && (
          <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1 py-0.5 text-[10px] font-medium">
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
          {video.published_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(video.published_at)}
            </span>
          )}
        </div>
      </div>

      {/* Status */}
      <div className="flex-shrink-0">
        <StatusBadge type="video" status={video.status} />
      </div>
    </Link>
  );
}
