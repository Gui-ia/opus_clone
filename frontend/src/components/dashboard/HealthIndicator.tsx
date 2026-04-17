import { useHealth } from '../../hooks/useHealth';

export function HealthIndicator() {
  const { data, isError } = useHealth();

  const services = [
    { name: 'PostgreSQL', status: data?.postgres },
    { name: 'Redis', status: data?.redis },
    { name: 'MinIO', status: data?.minio },
  ];

  return (
    <div className="flex items-center gap-3">
      {services.map(({ name, status }) => (
        <div key={name} className="group relative flex items-center gap-1.5">
          <div
            className={`h-2 w-2 rounded-full ${
              isError || !status
                ? 'bg-gray-600'
                : status === 'ok'
                  ? 'bg-green-400'
                  : 'bg-red-400'
            }`}
          />
          <span className="text-xs text-gray-500">{name}</span>
        </div>
      ))}
    </div>
  );
}
