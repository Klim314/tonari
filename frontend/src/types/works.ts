export interface WorkSourceMeta {
	[key: string]: unknown;
	homepage_url?: string;
	author?: string;
	description?: string;
	thumbnail_url?: string;
}

export interface Work {
	id: number;
	title: string;
	source?: string | null;
	source_id?: string | null;
	source_meta?: WorkSourceMeta | null;
}

export interface PaginatedWorksResponse {
	items: Work[];
	total: number;
	limit: number;
	offset: number;
}

export interface Chapter {
	id: number;
	work_id: number;
	idx: number | string;
	sort_key: number;
	title: string;
}

export interface ChapterDetail extends Chapter {
	normalized_text: string;
}

export interface PaginatedChaptersResponse {
	items: Chapter[];
	total: number;
	limit: number;
	offset: number;
}
