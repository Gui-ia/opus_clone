import { Loader2 } from 'lucide-react';

export function LoadingSpinner({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-16 ${className}`}>
      <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
    </div>
  );
}
