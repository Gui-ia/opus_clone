import { useState } from 'react';
import { Plus } from 'lucide-react';
import { ChannelCard } from '../components/channels/ChannelCard';
import { ChannelForm } from '../components/channels/ChannelForm';
import { Modal } from '../components/ui/Modal';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Pagination } from '../components/ui/Pagination';
import {
  useChannels,
  useCreateChannel,
  useUpdateChannel,
  useDeleteChannel,
} from '../hooks/useChannels';
import { usePagination } from '../hooks/usePagination';
import type { ChannelCreate, ChannelResponse, ChannelUpdate, Platform } from '../types/channel';

export function ChannelsPage() {
  const { page, pageSize, setPage } = usePagination();
  const [platformFilter, setPlatformFilter] = useState<Platform | ''>('');
  const [showForm, setShowForm] = useState(false);
  const [editChannel, setEditChannel] = useState<ChannelResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ChannelResponse | null>(null);

  const { data: channels, isLoading } = useChannels({
    platform: platformFilter || undefined,
    page,
    page_size: pageSize,
  });

  const createMutation = useCreateChannel();
  const updateMutation = useUpdateChannel();
  const deleteMutation = useDeleteChannel();

  const handleCreate = (data: ChannelCreate | ChannelUpdate) => {
    createMutation.mutate(data as ChannelCreate, {
      onSuccess: () => setShowForm(false),
    });
  };

  const handleEdit = (data: ChannelCreate | ChannelUpdate) => {
    if (!editChannel) return;
    updateMutation.mutate(
      { id: editChannel.id, data: data as ChannelUpdate },
      { onSuccess: () => setEditChannel(null) },
    );
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Canais</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700"
        >
          <Plus className="h-4 w-4" />
          Novo Canal
        </button>
      </div>

      {/* Filter */}
      <div className="mb-4">
        <select
          value={platformFilter}
          onChange={(e) => {
            setPlatformFilter(e.target.value as Platform | '');
            setPage(1);
          }}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300"
        >
          <option value="">Todas as plataformas</option>
          <option value="youtube">YouTube</option>
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
        </select>
      </div>

      {/* List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : !channels || channels.length === 0 ? (
        <EmptyState message="Nenhum canal cadastrado" />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {channels.map((ch) => (
              <ChannelCard
                key={ch.id}
                channel={ch}
                onEdit={setEditChannel}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
          <div className="mt-4">
            <Pagination
              page={page}
              pageSize={pageSize}
              itemCount={channels.length}
              onPageChange={setPage}
            />
          </div>
        </>
      )}

      {/* Create modal */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title="Novo Canal"
      >
        <ChannelForm
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          loading={createMutation.isPending}
        />
      </Modal>

      {/* Edit modal */}
      <Modal
        open={!!editChannel}
        onClose={() => setEditChannel(null)}
        title="Editar Canal"
      >
        <ChannelForm
          channel={editChannel}
          onSubmit={handleEdit}
          onCancel={() => setEditChannel(null)}
          loading={updateMutation.isPending}
        />
      </Modal>

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Desativar Canal"
        message={`Tem certeza que deseja desativar o canal "${deleteTarget?.display_name || deleteTarget?.username}"?`}
        confirmLabel="Desativar"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
