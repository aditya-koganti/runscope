import type { PropsWithChildren } from "react";

interface QueryStateProps extends PropsWithChildren {
  loading?: boolean;
  error?: boolean;
  onRetry?: () => void;
}

export function QueryState({ loading, error, onRetry, children }: QueryStateProps) {
  if (loading) {
    return (
      <div className="panel state-panel" aria-busy="true" aria-label="Loading content">
        <div className="skeleton skeleton-wide" />
        <div className="skeleton" />
        <div className="skeleton skeleton-short" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel state-panel" role="alert">
        <h2>We couldn't load this data</h2>
        <p>The API may be temporarily unavailable.</p>
        {onRetry ? (
          <button className="button button-secondary" onClick={onRetry} type="button">
            Retry
          </button>
        ) : null}
      </div>
    );
  }
  return children;
}
