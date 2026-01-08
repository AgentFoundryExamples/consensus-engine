/**
 * StatusBadge component for displaying run status
 */

interface StatusBadgeProps {
  status: 'queued' | 'running' | 'completed' | 'failed' | string;
  className?: string;
}

const statusConfig = {
  queued: {
    label: 'Queued',
    className: 'bg-gray-100 text-gray-800',
  },
  running: {
    label: 'Running',
    className: 'bg-blue-100 text-blue-800',
  },
  completed: {
    label: 'Completed',
    className: 'bg-green-100 text-green-800',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-800',
  },
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = statusConfig[status as keyof typeof statusConfig] || {
    label: status,
    className: 'bg-gray-100 text-gray-800',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className} ${className} `}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {config.label}
    </span>
  );
}
