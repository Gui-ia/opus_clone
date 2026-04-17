import { useState } from 'react';

export function usePagination(pageSize = 20) {
  const [page, setPage] = useState(1);

  return {
    page,
    pageSize,
    setPage,
    nextPage: () => setPage((p) => p + 1),
    prevPage: () => setPage((p) => Math.max(1, p - 1)),
    resetPage: () => setPage(1),
  };
}
