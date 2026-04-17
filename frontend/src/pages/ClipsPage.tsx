import { useState, useCallback, useMemo } from 'react';
import { ClipCard } from '../components/clips/ClipCard';
import { ClipDetailPanel } from '../components/clips/ClipDetailPanel';
import { BulkActionBar } from '../components/clips/BulkActionBar';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Pagination } from '../components/ui/Pagination';
import { useClips, useApproveClip, useRejectClip } from '../hooks/useClips';
import { usePagination } from '../hooks/usePagination';
import { TRANSIENT_CLIP_STATUSES } from '../types/clip';
import type { ClipResponse, ClipStatus, ClipApproval } from '../types/clip';
import { toast } from 'sonner';

const STATUS_OPTIONS: { value: '' | ClipStatus; label: string }[] = [
  { value: '', label: 'Todos os status' },
  { value: 'ready', label: 'Prontos p/ Revisao' },
  { value: 'approved', label: 'Aprovados' },
  { value: 'rejected', label: 'Rejeitados' },
  { value: 'published', label: 'Publicados' },
  { value: 'rendering', label: 'Renderizando' },
  { value: 'planned', label: 'Planejados' },
  { value: 'failed', label: 'Falhados' },
];

export function ClipsPage() {
  const { page, pageSize, setPage } = usePagination();
  const [statusFilter, setStatusFilter] = useState<'' | ClipStatus>('ready');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailClip, setDetailClip] = useState<ClipResponse | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  const refetchInterval = useMemo(() => {
    if (statusFilter && TRANSIENT_CLIP_STATUSES.includes(statusFilter as ClipStatus)) {
      return 10_000;
    }
    return 30_000;
  }, [statusFilter]);

  const { data: clips, isLoading } = useClips(
    {
      status: statusFilter || undefined,
      page,
      page_size: pageSize,
    },
    { refetchInterval },
  );

  const approveMutation = useApproveClip();
  const rejectMutation = useRejectClip();

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleApprove = (clipId: string, data?: ClipApproval) => {
    approveMutation.mutate({ id: clipId, data });
    setDetailClip(null);
  };

  const handleReject = (clipId: string) => {
    rejectMutation.mutate(clipId);
    setDetailClip(null);
  };

  const handleBulkApprove = async () => {
    setBulkLoading(true);
    const ids = Array.from(selectedIds);
    const results = await Promise.allSettled(
      ids.map((id) => approveMutation.mutateAsync({ id })),
    );
    const success = results.filter((r) => r.status === 'fulfilled').length;
    toast.success(`${success} de ${ids.length} clips aprovados`);
    setSelectedIds(new Set());
    setBulkLoading(false);
  };

  const handleBulkReject = async () => {
    setBulkLoading(true);
    const ids = Array.from(selectedIds);
    const results = await Promise.allSettled(
      ids.map((id) => rejectMutation.mutateAsync(id)),
    );
    const success = results.filter((r) => r.status === 'fulfilled').length;
    toast.success(`${success} de ${ids.length} clips rejeitados`);
    setSelectedIds(new Set());
    setBulkLoading(false);
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Clipes</h1>

      {/* Filter */}
      <div className="mb-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as '' | ClipStatus);
            setPage(1);
            setSelectedIds(new Set());
          }}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Grid */}
      {isLoading ? (
        <LoadingSpinner />
      ) : !clips || clips.length === 0 ? (
        <EmptyState message="Nenhum clip encontrado" />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {clips.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                selected={selectedIds.has(clip.id)}
                onSelect={toggleSelect}
                onClick={setDetailClip}
              />
            ))}
          </div>
          <div className="mt-4">
            <Pagination
              page={page}
              pageSize={pageSize}
              itemCount={clips.length}
              onPageChange={setPage}
            />
          </div>
        </>
      )}

      {/* Bulk actions */}
      <BulkActionBar
        count={selectedIds.size}
        onApproveAll={handleBulkApprove}
        onRejectAll={handleBulkReject}
        onClear={() => setSelectedIds(new Set())}
        loading={bulkLoading}
      />

      {/* Detail panel */}
      {detailClip && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/50"
            onClick={() => setDetailClip(null)}
          />
          <ClipDetailPanel
            clip={detailClip}
            onClose={() => setDetailClip(null)}
            onApprove={handleApprove}
            onReject={handleReject}
            loading={approveMutation.isPending || rejectMutation.isPending}
          />
        </>
      )}
    </div>
  );
}
