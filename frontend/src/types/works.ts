import type {
	ChapterDetailOut,
	ChapterGroupOut,
	ChapterOut,
	ChaptersWithGroupsResponse,
	PaginatedWorksOut,
	WorkOut,
} from "../client";

export type Work = WorkOut;
export type PaginatedWorksResponse = PaginatedWorksOut;
export type Chapter = ChapterOut;
export type ChapterGroup = ChapterGroupOut;
export type ChapterDetail = ChapterDetailOut;
export type PaginatedChaptersResponse = ChaptersWithGroupsResponse;
