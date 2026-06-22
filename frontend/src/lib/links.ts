import type { MouseEvent } from "react";

export function chapterPath(workId: number, chapterId: number): string {
	return `/works/${workId}/chapters/${chapterId}`;
}

export function isModifiedClick(e: MouseEvent): boolean {
	return (
		e.button !== 0 ||
		e.metaKey ||
		e.ctrlKey ||
		e.shiftKey ||
		e.altKey ||
		e.defaultPrevented
	);
}
