import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold text-gray-700">404</h1>
      <p className="mt-4 text-lg text-gray-400">Pagina nao encontrada</p>
      <Link
        to="/dashboard"
        className="mt-6 flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700"
      >
        <Home className="h-4 w-4" />
        Voltar ao Dashboard
      </Link>
    </div>
  );
}
