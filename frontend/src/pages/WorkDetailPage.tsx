import {
	Alert,
	Box,
	Button,
	Checkbox,
	Container,
	Field,
	HStack,
	Heading,
	Image,
	Input,
	Skeleton,
	Stack,
	Switch,
	Text,
} from "@chakra-ui/react";
import {
	type FormEvent,
	type MouseEvent,
	useCallback,
	useMemo,
	useState,
} from "react";
import { Works } from "../client";
import { AddToGroupModal } from "../components/AddToGroupModal";
import { ChapterGroupRow } from "../components/ChapterGroupRow";
import { CreateChapterGroupModal } from "../components/CreateChapterGroupModal";
import { WorkPromptSelector } from "../components/WorkPromptSelector";
import { Pagination } from "../components/common/Pagination";
import { useChapterSelection } from "../hooks/useChapterSelection";
import { useScrapeStatus } from "../hooks/useScrapeStatus";
import { useWork } from "../hooks/useWork";
import { useWorkChapters } from "../hooks/useWorkChapters";
import { getApiErrorMessage } from "../lib/api";
import type { Chapter } from "../types/works";

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

	// Scrape Status
	const handleChapterFound = useCallback(() => {
		// Simple refresh on chapter found
		setChaptersRefreshToken((prev) => prev + 1);
	}, []);

	const scrapeState = useScrapeStatus(workId, handleChapterFound);
	const isScraping =
		scrapeState.status === "pending" || scrapeState.status === "running";

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
			.map((item) => (item.data as Chapter).id);
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
				`/api/works/${workId}/chapter-groups/${groupId}`,
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

				{isScraping && (
					<Alert.Root status="info" mb={6} borderRadius="lg">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Scraping in progress... {scrapeState.progress} chapters found so
								far.
							</Alert.Description>
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
											const group = item.data as any; // Will be typed properly once API client regenerates
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
													<Text fontWeight="semibold" color="teal.200">
														Chapter {formatChapterKey(chapter.idx)}
													</Text>
													<Text>{chapter.title}</Text>
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
									Select the chapter range to scrape. Decimals (e.g. 2.1) are
									supported.
								</Text>
								<ScrapeChaptersInlineForm
									workId={workId}
									onSuccess={handleScrapeSuccess}
									isDisabled={isScraping}
								/>
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
			</Container>
		</Box>
	);
}

interface ScrapeFormProps {
	workId: number;
	onSuccess?: () => void;
	isDisabled?: boolean;
}

function ScrapeChaptersInlineForm({
	workId,
	onSuccess,
	isDisabled,
}: ScrapeFormProps) {
	const [start, setStart] = useState("");
	const [end, setEnd] = useState("");
	const [force, setForce] = useState(false);
	const [submitting, setSubmitting] = useState(false);
	const [feedback, setFeedback] = useState<{
		type: "success" | "error" | "warning";
		message: string;
	} | null>(null);

	async function handleSubmit(event: FormEvent) {
		event.preventDefault();
		const startValue = Number.parseFloat(start);
		const endValue = Number.parseFloat(end);
		if (Number.isNaN(startValue) || Number.isNaN(endValue)) {
			setFeedback({
				type: "warning",
				message: "Enter valid chapter numbers (e.g. 1 or 2.1).",
			});
			return;
		}
		if (endValue < startValue) {
			setFeedback({
				type: "warning",
				message: "End chapter must be after start chapter.",
			});
			return;
		}
		setSubmitting(true);
		try {
			await Works.requestChapterScrapeWorksWorkIdScrapeChaptersPost({
				path: { work_id: workId },
				body: {
					start: startValue,
					end: endValue,
					force,
				},
				throwOnError: true,
			});
			setStart("");
			setEnd("");
			setForce(false);
			setFeedback({ type: "success", message: "Scrape request queued." });
			onSuccess?.();
		} catch (error) {
			const message = getApiErrorMessage(error, "Failed to queue scrape");
			setFeedback({ type: "error", message });
		} finally {
			setSubmitting(false);
		}
	}

	return (
		<Box as="form" onSubmit={handleSubmit}>
			<Stack>
				{feedback && (
					<Alert.Root status={feedback.type} borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>{feedback.message}</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				)}
				<Field.Root required>
					<Field.Label>Start chapter</Field.Label>
					<Input
						type="text"
						placeholder="e.g. 1 or 2.1"
						value={start}
						onChange={(event) => setStart(event.target.value)}
					/>
				</Field.Root>
				<Field.Root required>
					<Field.Label>End chapter</Field.Label>
					<Input
						type="text"
						placeholder="e.g. 5 or 5.2"
						value={end}
						onChange={(event) => setEnd(event.target.value)}
					/>
				</Field.Root>
				<Switch.Root
					checked={force}
					onCheckedChange={({ checked }) => setForce(checked)}
					display="flex"
					alignItems="center"
					justifyContent="space-between"
					px={1}
				>
					<Switch.Label flex="1">Rescrape existing chapters</Switch.Label>
					<Switch.Control>
						<Switch.Thumb />
					</Switch.Control>
				</Switch.Root>
				<Button
					type="submit"
					colorScheme="teal"
					loading={submitting}
					disabled={isDisabled}
				>
					{isDisabled ? "Scrape in progress" : "Queue scrape"}
				</Button>
			</Stack>
		</Box>
	);
}

function sortChapters(chapters: Chapter[]) {
	return [...chapters].sort((a, b) => compareChapterKey(a.idx, b.idx));
}

function compareChapterKey(aKey: Chapter["idx"], bKey: Chapter["idx"]) {
	const aNum = Number(aKey);
	const bNum = Number(bKey);
	if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
		return aNum - bNum;
	}
	return String(aKey).localeCompare(String(bKey), undefined, { numeric: true });
}

function formatChapterKey(key: Chapter["idx"]) {
	if (typeof key === "number") {
		return Number.isInteger(key) ? String(key) : key.toFixed(2);
	}
	return key;
}
