import { Works } from "../client";

export async function regenerateChapterSegments(
	workId: number,
	chapterId: number,
) {
	await Works.regenerateChapterSegmentsWorksWorkIdChaptersChapterIdRegenerateSegmentsPost(
		{
			path: { work_id: workId, chapter_id: chapterId },
			throwOnError: true,
		},
	);
}
