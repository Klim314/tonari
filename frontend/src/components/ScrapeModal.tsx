import {
	Alert,
	Box,
	Button,
	Dialog,
	Field,
	Input,
	Progress,
	Stack,
	Switch,
	Text,
} from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import { Works } from "../client";
import { apiUrl } from "../clientConfig";
import { type ScrapeStatus, useScrapeStatus } from "../hooks/useScrapeStatus";
import { getApiErrorMessage } from "../lib/api";
import type { Chapter } from "../types/works";

interface ScrapeModalProps {
	workId: number;
	isOpen: boolean;
	onClose: () => void;
	onSuccess: () => void;
}

type ModalState = "input" | "scraping" | "completed" | "partial";

const STATUS_LABELS: Record<ScrapeStatus, string> = {
	pending: "Pending",
	running: "Running",
	completed: "Completed",
	partial: "Partial",
	failed: "Failed",
	idle: "Idle",
};

export function ScrapeModal({
	workId,
	isOpen,
	onClose,
	onSuccess,
}: ScrapeModalProps) {
	const [start, setStart] = useState("");
	const [end, setEnd] = useState("");
	const [force, setForce] = useState(false);
	const [modalState, setModalState] = useState<ModalState>("input");
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [chaptersFound, setChaptersFound] = useState<number>(0);
	const [isTrackingScrape, setIsTrackingScrape] = useState(false);

	// Log of recent activities (optional, but nice)
	const [logs, setLogs] = useState<{ id: number; msg: string }[]>([]);
	const logIdRef = useRef(0);
	const addLog = (msg: string) =>
		setLogs((prev) => [{ id: logIdRef.current++, msg }, ...prev].slice(0, 5));

	// Hook handles the SSE connection
	const scrapeStatus = useScrapeStatus(
		// Only connect when modal is open
		isOpen ? workId : -1,
		() => {
			setChaptersFound((prev) => prev + 1);
			addLog("Chapter found.");
		},
	);

	// Fetch latest chapter info for auto-population
	useEffect(() => {
		if (isOpen && modalState === "input") {
			const fetchLatest = async () => {
				try {
					// 1. Get total count
					const initialRes =
						await Works.listChaptersForWorkWorksWorkIdChaptersGet({
							path: { work_id: workId },
							query: { limit: 1, offset: 0 },
						});
					const total = initialRes?.data?.total_items || 0;

					if (initialRes?.data && total === 0) {
						setStart("1");
						setEnd("5");
						return;
					}

					// 2. Get last item
					const lastItemRes =
						await Works.listChaptersForWorkWorksWorkIdChaptersGet({
							path: { work_id: workId },
							query: { limit: 1, offset: total - 1 },
						});

					if (lastItemRes?.data?.items && lastItemRes.data.items.length > 0) {
						const lastItem = lastItemRes.data.items[0];
						if (lastItem.item_type === "chapter") {
							const chapter = lastItem.data as Chapter;
							// Assuming numerical sort_key/idx for now as requested
							// Using Math.floor/ceil to be safe with floats
							const lastIdx = Math.floor(Number(chapter.idx));
							if (!Number.isNaN(lastIdx)) {
								setStart(String(lastIdx + 1));
								setEnd(String(lastIdx + 5));
							}
						} else {
							// Fallback if last item is a group (less likely to simple sequential scrape)
							setStart("1");
							setEnd("5");
						}
					}
				} catch (e) {
					console.warn("Failed to auto-populate scrape range", e);
					// Fallback
					setStart("1");
					setEnd("5");
				}
			};
			fetchLatest();
		}
	}, [isOpen, workId, modalState]);

	// Reset state when opening
	useEffect(() => {
		if (isOpen) {
			setModalState("input"); // Default to input
			setSubmitError(null);
			setChaptersFound(0);
			setLogs([]);
			setIsTrackingScrape(false);
			// Don't reset start/end here, let the auto-populator do it
			setForce(false);
		}
	}, [isOpen]);

	// Sync modal state with scrape status
	useEffect(() => {
		if (!isOpen) return;

		if (
			scrapeStatus.status === "running" ||
			scrapeStatus.status === "pending"
		) {
			setIsTrackingScrape(true);
			setModalState("scraping");
		} else if (scrapeStatus.status === "completed" && isTrackingScrape) {
			setModalState("completed");
		} else if (scrapeStatus.status === "partial" && isTrackingScrape) {
			setModalState("partial");
		}
	}, [scrapeStatus.status, isOpen, isTrackingScrape]);

	const handleQueueScrape = async () => {
		const startValue = Number.parseFloat(start);
		const endValue = Number.parseFloat(end);

		if (Number.isNaN(startValue) || Number.isNaN(endValue)) {
			setSubmitError("Please enter valid numbers.");
			return;
		}

		setSubmitError(null);
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
			setIsTrackingScrape(true);
			setModalState("scraping");
			setChaptersFound(0);
			setLogs(["Scrape queued..."]);
		} catch (err) {
			setSubmitError(getApiErrorMessage(err, "Failed to queue scrape"));
		}
	};

	const handleCancel = async () => {
		// Call backend cancel
		try {
			await fetch(apiUrl(`/works/${workId}/scrape-cancel`), { method: "POST" });
		} catch (e) {
			console.error("Failed to cancel scrape", e);
		}
		onClose();
	};

	const handleClose = () => {
		if (modalState === "scraping") {
			handleCancel();
		} else {
			if (modalState === "completed" || modalState === "partial") {
				onSuccess(); // Refresh list on completion or partial success
			}
			onClose();
		}
	};

	const statusLabel = STATUS_LABELS[scrapeStatus.status];
	const isTerminal = modalState === "completed" || modalState === "partial";

	return (
		<Dialog.Root
			open={isOpen}
			onOpenChange={(details) => {
				if (!details.open) handleClose();
			}}
			closeOnInteractOutside={false} // Prevent accidental closes while scraping
		>
			<Dialog.Backdrop />
			<Dialog.Positioner>
				<Dialog.Content>
					<Dialog.CloseTrigger />
					<Dialog.Header>
						<Dialog.Title>
							{modalState === "input"
								? "Scrape Chapters"
								: modalState === "scraping"
									? "Scraping in Progress"
									: modalState === "partial"
										? "Scrape Partially Complete"
										: "Scrape Complete"}
						</Dialog.Title>
					</Dialog.Header>

					<Dialog.Body>
						{modalState === "input" && (
							<Stack gap={4}>
								{submitError && (
									<Alert.Root status="error">
										<Alert.Indicator />
										<Alert.Content>
											<Alert.Description>{submitError}</Alert.Description>
										</Alert.Content>
									</Alert.Root>
								)}
								<Text fontSize="sm" color="gray.500">
									Enter the range of chapters to scrape.
								</Text>
								<Field.Root required>
									<Field.Label>Start Chapter</Field.Label>
									<Input
										value={start}
										onChange={(e) => setStart(e.target.value)}
										placeholder="e.g. 1"
									/>
								</Field.Root>
								<Field.Root required>
									<Field.Label>End Chapter</Field.Label>
									<Input
										value={end}
										onChange={(e) => setEnd(e.target.value)}
										placeholder="e.g. 10"
									/>
								</Field.Root>
								<Switch.Root
									checked={force}
									onCheckedChange={({ checked }) => setForce(checked)}
									display="flex"
									alignItems="center"
									justifyContent="space-between"
								>
									<Switch.Label>Rescrape existing chapters</Switch.Label>
									<Switch.Control>
										<Switch.Thumb />
									</Switch.Control>
								</Switch.Root>
							</Stack>
						)}

						{(modalState === "scraping" || isTerminal) && (
							<Stack gap={6} py={4}>
								<Box>
									<Text mb={2} fontSize="sm" fontWeight="medium">
										Status: {statusLabel}
									</Text>
									<Progress.Root
										value={
											scrapeStatus.total > 0
												? (scrapeStatus.progress / scrapeStatus.total) * 100
												: undefined
										}
										colorPalette={
											modalState === "partial"
												? "orange"
												: scrapeStatus.status === "failed"
													? "red"
													: "teal"
										}
									>
										<Progress.Track>
											<Progress.Range />
										</Progress.Track>
									</Progress.Root>
									<Text mt={1} fontSize="xs" color="gray.500" textAlign="right">
										{scrapeStatus.progress} / {scrapeStatus.total || "?"}
									</Text>
								</Box>

								{chaptersFound > 0 && (
									<Alert.Root status="info" variant="subtle">
										<Alert.Indicator />
										<Alert.Content>
											<Alert.Description>
												{chaptersFound} new/updated chapters found within this
												session.
											</Alert.Description>
										</Alert.Content>
									</Alert.Root>
								)}

								{scrapeStatus.error && (
									<Alert.Root status="error">
										<Alert.Indicator />
										<Alert.Content>
											<Alert.Description>
												Error: {scrapeStatus.error}
											</Alert.Description>
										</Alert.Content>
									</Alert.Root>
								)}

								{scrapeStatus.chapterErrors.length > 0 && (
									<Box>
										<Text
											fontSize="sm"
											fontWeight="medium"
											mb={2}
											color="red.600"
										>
											Failed chapters ({scrapeStatus.chapterErrors.length})
										</Text>
										<Box
											bg="red.50"
											p={2}
											borderRadius="md"
											fontSize="xs"
											color="red.700"
											maxH="120px"
											overflowY="auto"
										>
											{scrapeStatus.chapterErrors.map((err) => (
												<Text key={`${err.chapter}-${err.reason}`}>
													Ch. {err.chapter}: {err.reason}
												</Text>
											))}
										</Box>
									</Box>
								)}

								{/* Simple Log View */}
								{logs.length > 0 && (
									<Box
										bg="gray.50"
										p={2}
										borderRadius="md"
										fontSize="xs"
										color="gray.600"
										maxH="100px"
										overflowY="auto"
									>
										{logs.map((log) => (
											<Text key={log.id}>{log.msg}</Text>
										))}
									</Box>
								)}
							</Stack>
						)}
					</Dialog.Body>

					<Dialog.Footer>
						{modalState === "input" && (
							<>
								<Button variant="ghost" onClick={onClose}>
									Cancel
								</Button>
								<Button colorPalette="teal" onClick={handleQueueScrape}>
									Start Scrape
								</Button>
							</>
						)}

						{modalState === "scraping" && (
							<Button
								colorPalette="red"
								variant="subtle"
								onClick={handleCancel}
							>
								Stop & Close
							</Button>
						)}

						{modalState === "completed" && (
							<Button colorPalette="teal" onClick={handleClose}>
								Close & Refresh
							</Button>
						)}

						{modalState === "partial" && (
							<Button colorPalette="orange" onClick={handleClose}>
								Close & Refresh
							</Button>
						)}
					</Dialog.Footer>
				</Dialog.Content>
			</Dialog.Positioner>
		</Dialog.Root>
	);
}
