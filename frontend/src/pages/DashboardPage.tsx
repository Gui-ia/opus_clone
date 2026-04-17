import { Radio, Video, Scissors, Upload } from 'lucide-react';
import { StatCard } from '../components/dashboard/StatCard';
import { HealthIndicator } from '../components/dashboard/HealthIndicator';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useChannels } from '../hooks/useChannels';
import { useVideos } from '../hooks/useVideos';
import { useClips } from '../hooks/useClips';
import { TRANSIENT_VIDEO_STATUSES } from '../types/video';

export function DashboardPage() {
  const { data: channels } = useChannels({ page_size: 100 });
  const { data: videos, isLoading: loadingVideos } = useVideos({ page_size: 100 });
  const { data: readyClips } = useClips({ status: 'ready', page_size: 100 });
  const { data: publishedClips } = useClips({ status: 'published', page_size: 100 });
  const { data: recentClips } = useClips({ page_size: 10 });

  const activeChannels = channels?.filter((c) => c.is_active).length ?? 0;
  const processingVideos =
    videos?.filter((v) => TRANSIENT_VIDEO_STATUSES.includes(v.status)).length ?? 0;
  const clipsForReview = readyClips?.length ?? 0;
  const publishedCount = publishedClips?.length ?? 0;

  if (loadingVideos) return <LoadingSpinner />;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Radio className="h-5 w-5 text-violet-400" />}
          label="Canais Ativos"
          value={activeChannels}
          color="bg-violet-500/10"
        />
        <StatCard
          icon={<Video className="h-5 w-5 text-blue-400" />}
          label="Videos Processando"
          value={processingVideos}
          color="bg-blue-500/10"
        />
        <StatCard
          icon={<Scissors className="h-5 w-5 text-cyan-400" />}
          label="Clipes p/ Revisao"
          value={clipsForReview}
          color="bg-cyan-500/10"
        />
        <StatCard
          icon={<Upload className="h-5 w-5 text-green-400" />}
          label="Clipes Publicados"
          value={publishedCount}
          color="bg-green-500/10"
        />
      </div>

      {/* Bottom section */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Activity */}
        <div className="lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold">Atividade Recente</h2>
          <ActivityFeed
            videos={videos?.slice(0, 5) ?? []}
            clips={recentClips?.slice(0, 5) ?? []}
          />
        </div>

        {/* Health */}
        <div>
          <h2 className="mb-4 text-lg font-semibold">Status do Sistema</h2>
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            <HealthIndicator />
          </div>
        </div>
      </div>
    </div>
  );
}
