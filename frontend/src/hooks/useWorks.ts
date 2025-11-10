import { useEffect, useState } from 'react';
import { apiClient } from '../lib/api';
import type { PaginatedWorksResponse } from '../types/works';

interface WorksState {
  data: PaginatedWorksResponse | null;
  loading: boolean;
  error: string | null;
}

const defaultState: WorksState = {
  data: null,
  loading: false,
  error: null,
};

export function useWorks(searchQuery: string, refreshToken = 0) {
  const [state, setState] = useState<WorksState>(defaultState);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function fetchWorks() {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const params = new URLSearchParams();
        params.set('limit', '50');
        params.set('offset', '0');
        if (searchQuery.trim()) {
          params.set('q', searchQuery.trim());
        }

        const response = await apiClient.get<PaginatedWorksResponse>('/works/', {
          params,
          signal: controller.signal,
        });

        if (!cancelled) {
          setState({
            data: response.data,
            loading: false,
            error: null,
          });
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) {
          return;
        }
        setState({
          data: null,
          loading: false,
          error: error instanceof Error ? error.message : 'Failed to fetch works',
        });
      }
    }

    fetchWorks();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [searchQuery, refreshToken]);

  return state;
}
