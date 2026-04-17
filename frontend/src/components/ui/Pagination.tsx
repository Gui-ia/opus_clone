import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Props {
  page: number;
  pageSize: number;
  itemCount: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, itemCount, onPageChange }: Props) {
  const hasNext = itemCount === pageSize;
  const hasPrev = page > 1;

  if (!hasPrev && !hasNext) return null;

  return (
    <div className="flex items-center justify-between border-t border-gray-800 pt-4">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={!hasPrev}
        className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ChevronLeft className="h-4 w-4" />
        Anterior
      </button>
      <span className="text-sm text-gray-500">Pagina {page}</span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={!hasNext}
        className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Proxima
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
