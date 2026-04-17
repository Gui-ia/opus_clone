import { Inbox } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  message?: string;
  icon?: ReactNode;
}

export function EmptyState({
  message = 'Nenhum item encontrado',
  icon,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      {icon || <Inbox className="mb-3 h-12 w-12" />}
      <p className="text-sm">{message}</p>
    </div>
  );
}
