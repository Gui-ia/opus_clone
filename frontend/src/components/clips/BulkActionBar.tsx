import { Check, X as XIcon } from 'lucide-react';

interface Props {
  count: number;
  onApproveAll: () => void;
  onRejectAll: () => void;
  onClear: () => void;
  loading?: boolean;
}

export function BulkActionBar({
  count,
  onApproveAll,
  onRejectAll,
  onClear,
  loading,
}: Props) {
  if (count === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-4 rounded-xl border border-gray-700 bg-gray-900 px-6 py-3 shadow-2xl">
      <span className="text-sm text-gray-300">
        {count} clip{count > 1 ? 's' : ''} selecionado{count > 1 ? 's' : ''}
      </span>
      <div className="h-5 w-px bg-gray-700" />
      <button
        onClick={onApproveAll}
        disabled={loading}
        className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
      >
        <Check className="h-4 w-4" />
        Aprovar Todos
      </button>
      <button
        onClick={onRejectAll}
        disabled={loading}
        className="flex items-center gap-1.5 rounded-lg bg-red-600/20 px-3 py-1.5 text-sm font-medium text-red-400 transition-colors hover:bg-red-600/30 disabled:opacity-50"
      >
        <XIcon className="h-4 w-4" />
        Rejeitar Todos
      </button>
      <button
        onClick={onClear}
        className="text-sm text-gray-500 transition-colors hover:text-gray-300"
      >
        Limpar
      </button>
    </div>
  );
}
