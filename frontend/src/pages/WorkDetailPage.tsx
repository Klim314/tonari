import {
	Alert,
	Badge,
	Box,
	Button,
	Checkbox,
	Container,
	Heading,
	HStack,
	Image,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { type MouseEvent, useMemo, useState } from "react";
import { apiUrl } from "../clientConfig";
import { AddToGroupModal } from "../components/AddToGroupModal";
import { ChapterGroupRow } from "../components/ChapterGroupRow";
import { CreateChapterGroupModal } from "../components/CreateChapterGroupModal";
import { Pagination } from "../components/common/Pagination";
import { ScrapeModal } from "../components/ScrapeModal";
import { WorkPromptSelector } from "../components/WorkPromptSelector";
import { useChapterSelection } from "../hooks/useChapterSelection";
import { useWork } from "../hooks/useWork";
import { useWorkChapters } from "../hooks/useWorkChapters";
import { getApiErrorMessage } from "../lib/api";
import type { Chapter, ChapterGroup } from "../types/works";

const CHAPTERS_PER_PAGE = 10;
const CHAPTER_SKELETON_KEYS = Array.from(
	{ length: CHAPTERS_PER_PAGE },
	(_, index) => `chapter-skeleton-${index}`,
);

interface WorkDetailPageProps {
	workId: number;
	onNavigateHome: () => void;
	onNavigateToChapter?: (chapterId: number) => void;
}

export function WorkDetailPage({
	workId,
	onNavigateHome,
	onNavigateToChapter,
}: WorkDetailPageProps) {
	const [chapterPage, setChapterPage] = useState(0);
	const [chaptersRefreshToken, setChaptersRefreshToken] = useState(0);
	const [manageMode, setManageMode] = useState(false);
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [showAddToGroupModal, setShowAddToGroupModal] = useState(false);
	const [showScrapeModal, setShowScrapeModal] = useState(false);
	const chapterSelection = useChapterSelection();

	const {
		data: work,
		loading: workLoading,
		error: workError,
	} = useWork(workId);
	const {
		data: chaptersData,
		loading: chaptersLoading,
		error: chaptersError,
	} = useWorkChapters(
		workId,
		CHAPTERS_PER_PAGE,
		chapterPage * CHAPTERS_PER_PAGE,
		chaptersRefreshToken,
	);

	const meta = (work?.source_meta ?? {}) as Record<string, unknown>;
	const thumbnailUrl =
		typeof meta.thumbnail_url === "string" ? meta.thumbnail_url : undefined;
	const description =
		typeof meta.description === "string" && meta.description.trim().length > 0
			? meta.description
			: "No description available for this work yet.";

	// Handle mixed list of chapters and groups
	const items = useMemo(() => {
		if (!chaptersData?.items) return [];
		// Items are already sorted by the backend
		return chaptersData.items;
	}, [chaptersData?.items]);

	// Build list of visible chapter IDs for shift-click range selection
	const visibleChapterIds = useMemo(() => {
		return items
			.filter((item) => item.item_type === "chapter")
			.map((item) => {
				const chapter = item.data as Chapter;
				return chapter.id;
			});
	}, [items]);

	const totalItems = chaptersData?.total_items ?? 0;
	const totalChapters = chaptersData?.total_chapters ?? 0;
	const totalGroups = chaptersData?.total_groups ?? 0;
	const currentOffset = chaptersData?.offset ?? chapterPage * CHAPTERS_PER_PAGE;
	const showingStart = items.length > 0 ? currentOffset + 1 : 0;
	const showingEnd = currentOffset + items.length;
	const totalPages = Math.max(1, Math.ceil(totalItems / CHAPTERS_PER_PAGE));

	const handleScrapeSuccess = () => {
		// Scrape requested successfully
		setChapterPage(0);
		// We don't need to force refresh here immediately as the SSE will trigger updates
		// But refreshing once is good to catch the first empty state if any
		setChaptersRefreshToken((token) => token + 1);
	};

	const handleGroupCreated = () => {
		// Refresh chapters list to show new group
		setChaptersRefreshToken((prev) => prev + 1);
		chapterSelection.clearSelection();
		setManageMode(false);
	};

	const handleDeleteGroup = async (groupId: number) => {
		if (!window.confirm("Delete this group? Chapters will be ungrouped.")) {
			return;
		}

		try {
			const response = await fetch(
				apiUrl(`/works/${workId}/chapter-groups/${groupId}`),
				{
					method: "DELETE",
				},
			);

			if (!response.ok) {
				throw new Error("Failed to delete group");
			}

			// Refresh chapters list
			setChaptersRefreshToken((prev) => prev + 1);
		} catch (error) {
			alert(getApiErrorMessage(error, "Failed to delete group"));
		}
	};

	const handleToggleManageMode = (checked: boolean) => {
		setManageMode(checked);
		if (!checked) {
			chapterSelection.clearSelection();
		}
	};

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Button variant="ghost" mb={4} onClick={onNavigateHome}>
					← Back to works
				</Button>
				{workLoading ? (
					<Skeleton height="220px" borderRadius="lg" />
				) : workError ? (
					<Alert.Root status="error" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Failed to load work: {workError}
							</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : work ? (
					<Stack
						direction={{ base: "column", md: "row" }}
						borderWidth="1px"
						borderRadius="lg"
						p={6}
						mb={8}
					>
						{thumbnailUrl && (
							<Image
								src={thumbnailUrl}
								alt={`${work.title} thumbnail`}
								borderRadius="md"
								objectFit="cover"
								maxW={{ base: "100%", md: "250px" }}
							/>
						)}
						<Stack>
							<Heading size="lg">{work.title}</Heading>
							<Text color="gray.400" whiteSpace="pre-wrap">
								{description}
							</Text>
						</Stack>
					</Stack>
				) : (
					<Alert.Root status="warning" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>Work not found.</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				)}

				<Stack direction={{ base: "column", lg: "row" }} align="flex-start">
					<Box flex="2" w="full">
						<HStack justify="space-between" mb={4}>
							<Heading size="md">Chapters</Heading>
							<Button
								size="sm"
								variant={manageMode ? "solid" : "outline"}
								colorPalette="teal"
								onClick={() => handleToggleManageMode(!manageMode)}
							>
								{manageMode ? "Done Managing" : "Manage Chapters"}
							</Button>
						</HStack>

						{manageMode && chapterSelection.hasSelection && (
							<HStack mb={4} gap={2}>
								<Button
									colorPalette="teal"
									onClick={() => setShowCreateModal(true)}
								>
									Create Group ({chapterSelection.selectionCount})
								</Button>
								<Button
									variant="outline"
									colorPalette="teal"
									onClick={() => setShowAddToGroupModal(true)}
								>
									Add to Group
								</Button>
							</HStack>
						)}

						{chaptersLoading ? (
							<Stack>
								{CHAPTER_SKELETON_KEYS.map((key) => (
									<Skeleton key={key} height="72px" borderRadius="md" />
								))}
							</Stack>
						) : chaptersError ? (
							<Alert.Root status="error" borderRadius="md" mb={4}>
								<Alert.Indicator />
								<Alert.Content>
									<Alert.Description>
										Failed to load chapters: {chaptersError}
									</Alert.Description>
								</Alert.Content>
							</Alert.Root>
						) : items.length === 0 ? (
							<Box borderWidth="1px" borderRadius="md" p={6}>
								<Text color="gray.400">No chapters scraped yet.</Text>
							</Box>
						) : (
							<Stack>
								{(() => {
									let chapterIndex = 0;
									return items.map((item) => {
										if (item.item_type === "group") {
											const group = item.data as ChapterGroup;
											return (
												<ChapterGroupRow
													key={`group-${group.id}`}
													group={group}
													onNavigateToChapter={onNavigateToChapter}
													onDelete={() => handleDeleteGroup(group.id)}
													manageMode={manageMode}
												/>
											);
										}
										const chapter = item.data as Chapter;
										const currentIndex = chapterIndex++;
										const handleChapterClick = (e: MouseEvent) => {
											if (manageMode) {
												chapterSelection.toggleChapter(
													chapter.id,
													currentIndex,
													e.shiftKey,
													visibleChapterIds,
												);
											} else if (onNavigateToChapter) {
												onNavigateToChapter(chapter.id);
											}
										};
										return (
											<HStack key={`chapter-${chapter.id}`} gap={2}>
												{manageMode && (
													<Checkbox.Root
														checked={chapterSelection.isSelected(chapter.id)}
													>
														<Checkbox.HiddenInput />
														<Checkbox.Control
															onClick={(e: MouseEvent) => {
																e.stopPropagation();
																chapterSelection.toggleChapter(
																	chapter.id,
																	currentIndex,
																	e.shiftKey,
																	visibleChapterIds,
																);
															}}
														/>
													</Checkbox.Root>
												)}
												<Box
													flex="1"
													borderWidth="1px"
													borderRadius="md"
													p={4}
													as="button"
													textAlign="left"
													cursor="pointer"
													transition="background-color 0.2s ease"
													_hover={{ bg: "gray.800" }}
													onClick={handleChapterClick}
												>
													<HStack justify="space-between" align="flex-start">
														<Box>
															<Text fontWeight="semibold" color="teal.200">
																Chapter {formatChapterKey(chapter.idx)}
															</Text>
															<Text>{chapter.title}</Text>
														</Box>
														{chapter.is_fully_translated && (
															<Badge colorPalette="green" variant="subtle">
																Translated
															</Badge>
														)}
													</HStack>
												</Box>
											</HStack>
										);
									});
								})()}
							</Stack>
						)}
						<Box mt={6}>
							<Pagination
								currentPage={chapterPage}
								totalPages={totalPages}
								onPageChange={setChapterPage}
							/>
							{totalGroups > 0 && (
								<Text fontSize="sm" color="gray.400" mt={2} textAlign="center">
									Showing {showingStart}-{showingEnd} of {totalItems} items (
									{totalChapters} chapters, {totalGroups}{" "}
									{totalGroups === 1 ? "group" : "groups"})
								</Text>
							)}
						</Box>
					</Box>

					<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
						<Stack gap={6}>
							<Box>
								<Heading size="md" mb={4}>
									Prompt
								</Heading>
								<WorkPromptSelector workId={workId} />
							</Box>

							<Box borderTopWidth="1px" pt={6}>
								<Heading size="md" mb={4}>
									Scrape Chapters
								</Heading>
								<Text fontSize="sm" color="gray.400" mb={4}>
									Scrape new chapters or update existing ones.
								</Text>
								<Button
									width="full"
									variant="outline"
									colorPalette="teal"
									onClick={() => setShowScrapeModal(true)}
								>
									Open Scrape Tools
								</Button>
							</Box>
						</Stack>
					</Box>
				</Stack>

				{/* Create Chapter Group Modal */}
				<CreateChapterGroupModal
					workId={workId}
					selectedChapterIds={Array.from(chapterSelection.selectedChapterIds)}
					isOpen={showCreateModal}
					onClose={() => setShowCreateModal(false)}
					onSuccess={handleGroupCreated}
				/>

				{/* Add to Existing Group Modal */}
				<AddToGroupModal
					workId={workId}
					selectedChapterIds={Array.from(chapterSelection.selectedChapterIds)}
					isOpen={showAddToGroupModal}
					onClose={() => setShowAddToGroupModal(false)}
					onSuccess={handleGroupCreated}
				/>

				<ScrapeModal
					workId={workId}
					isOpen={showScrapeModal}
					onClose={() => setShowScrapeModal(false)}
					onSuccess={handleScrapeSuccess}
				/>
			</Container>
		</Box>
	);
}

function formatChapterKey(key: Chapter["idx"]) {
	if (typeof key === "number") {
		return Number.isInteger(key) ? String(key) : key.toFixed(2);
	}
	return key;
}
