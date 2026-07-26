interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}

export function Pagination({ page, pages, total, onPage }: PaginationProps) {
  return (
    <div className="pagination" aria-label="Pagination">
      <span>
        Page {pages ? page : 0} of {pages} · {total} total
      </span>
      <div>
        <button
          className="button button-secondary"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          type="button"
        >
          Previous
        </button>
        <button
          className="button button-secondary"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          type="button"
        >
          Next
        </button>
      </div>
    </div>
  );
}
