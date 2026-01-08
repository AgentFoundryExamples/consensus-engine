/**
 * Header component with accessible navigation
 */

interface HeaderProps {
  title?: string;
}

export function Header({ title = 'Consensus Engine' }: HeaderProps) {
  return (
    <header className="border-b border-gray-200 bg-white" role="banner">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      </div>
    </header>
  );
}
