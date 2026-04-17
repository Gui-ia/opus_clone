import type { ReactNode } from 'react';

interface Props {
  icon: ReactNode;
  label: string;
  value: number | string;
  color: string;
}

export function StatCard({ icon, label, value, color }: Props) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2.5 ${color}`}>{icon}</div>
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  );
}
