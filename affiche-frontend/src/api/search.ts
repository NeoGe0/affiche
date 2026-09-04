import { api } from './client';
import type { SearchResults } from '../types';

export const searchApi = {

  searchItems: (search: string, pageSize = 25) => {
    const params = new URLSearchParams({ search, page_size: String(pageSize) });
    return api.get<SearchResults>(`/search/items?${params}`);
  },
};
