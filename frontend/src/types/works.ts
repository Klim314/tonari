export interface Work {
  id: number;
  title: string;
}

export interface PaginatedWorksResponse {
  items: Work[];
  total: number;
  limit: number;
  offset: number;
}
