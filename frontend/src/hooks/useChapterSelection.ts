import { useCallback, useRef, useState } from "react";

/**
 * Hook for managing multi-select state of chapters.
 * Used in "Manage Chapters" mode to select chapters for grouping.
 * Supports shift-click for range selection.
 */
export function useChapterSelection() {
	const [selectedChapterIds, setSelectedChapterIds] = useState<Set<number>>(
		new Set(),
	);
	// Track the last clicked chapter index for shift-click range selection
	const lastClickedIndexRef = useRef<number | null>(null);

	/**
	 * Toggle a single chapter's selection.
	 * @param chapterId - The chapter ID to toggle
	 * @param index - The index of this chapter in the visible list
	 * @param shiftKey - Whether shift was held during click
	 * @param visibleChapterIds - Array of chapter IDs in display order (for range selection)
	 */
	const toggleChapter = useCallback(
		(
			chapterId: number,
			index?: number,
			shiftKey?: boolean,
			visibleChapterIds?: number[],
		) => {
			// Shift-click range selection
			if (
				shiftKey &&
				index !== undefined &&
				lastClickedIndexRef.current !== null &&
				visibleChapterIds
			) {
				const start = Math.min(lastClickedIndexRef.current, index);
				const end = Math.max(lastClickedIndexRef.current, index);
				const rangeIds = visibleChapterIds.slice(start, end + 1);

				setSelectedChapterIds((prev) => {
					const next = new Set(prev);
					for (const id of rangeIds) {
						next.add(id);
					}
					return next;
				});
				// Update last clicked to current
				lastClickedIndexRef.current = index;
				return;
			}

			// Regular click - toggle single chapter
			setSelectedChapterIds((prev) => {
				const next = new Set(prev);
				if (next.has(chapterId)) {
					next.delete(chapterId);
				} else {
					next.add(chapterId);
				}
				return next;
			});

			// Update last clicked index
			if (index !== undefined) {
				lastClickedIndexRef.current = index;
			}
		},
		[],
	);

	const selectAll = useCallback((chapterIds: number[]) => {
		setSelectedChapterIds(new Set(chapterIds));
	}, []);

	const clearSelection = useCallback(() => {
		setSelectedChapterIds(new Set());
		lastClickedIndexRef.current = null;
	}, []);

	const isSelected = useCallback(
		(chapterId: number) => selectedChapterIds.has(chapterId),
		[selectedChapterIds],
	);

	return {
		selectedChapterIds,
		toggleChapter,
		selectAll,
		clearSelection,
		isSelected,
		hasSelection: selectedChapterIds.size > 0,
		selectionCount: selectedChapterIds.size,
	};
}
