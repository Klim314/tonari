import {
	Alert,
	Box,
	Button,
	Container,
	HStack,
	Skeleton,
	Stack,
} from "@chakra-ui/react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import type { ChapterDetail, Work } from "../../types/works";
import { ChapterHeaderCard } from "./ChapterHeaderCard";
import { TranslationPanel } from "./translation/TranslationPanel";
import type { TranslationPanelProps } from "./translation/TranslationPanel";
import type { PromptMeta } from "./types";

interface ChapterNavigationProps {
	nextId?: number | null;
	prevId?: number | null;
	onNavigate: (chapterId: number) => void;
}

function ChapterNavigation({
	nextId,
	prevId,
	onNavigate,
}: ChapterNavigationProps) {
	return (
		<HStack justify="space-between" width="full">
			<Button
				disabled={!prevId}
				variant="ghost"
				onClick={() => prevId && onNavigate(prevId)}
				visibility={prevId ? "visible" : "hidden"}
			>
				<ArrowLeft /> Previous Chapter
			</Button>
			<Button
				disabled={!nextId}
				variant="ghost"
				onClick={() => nextId && onNavigate(nextId)}
				visibility={nextId ? "visible" : "hidden"}
			>
				Next Chapter <ArrowRight />
			</Button>
		</HStack>
	);
}

export interface ChapterDetailViewProps {
	work: Work | null;
	chapter: ChapterDetail | null;
	promptMeta: PromptMeta;
	promptDrawerTrigger: ReactNode;
	translationPanelProps: TranslationPanelProps;
	onNavigateBack: () => void;
	onNavigateChapter: (chapterId: number) => void;
	onRegenerateSegments: () => void;
	isRegeneratingSegments: boolean;
	isLoading: boolean;
	errorMessage: string | null;
}

export function ChapterDetailView({
	work,
	chapter,
	promptMeta,
	promptDrawerTrigger,
	translationPanelProps,
	onNavigateBack,
	onNavigateChapter,
	onRegenerateSegments,
	isRegeneratingSegments,
	isLoading,
	errorMessage,
}: ChapterDetailViewProps) {
	if (isLoading) {
		return (
			<Box py={10}>
				<Container maxW="6xl">
					<Stack gap={4}>
						<Skeleton height="32px" borderRadius="md" />
						<Skeleton height="420px" borderRadius="lg" />
					</Stack>
				</Container>
			</Box>
		);
	}

	if (errorMessage) {
		return (
			<Box py={10}>
				<Container maxW="6xl">
					<Button variant="ghost" mb={4} onClick={onNavigateBack}>
						← Back to work
					</Button>
					<Alert.Root status="error" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Failed to load chapter: {errorMessage}
							</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				</Container>
			</Box>
		);
	}

	if (!work || !chapter) {
		return (
			<Box py={10}>
				<Container maxW="6xl">
					<Button variant="ghost" mb={4} onClick={onNavigateBack}>
						← Back to work
					</Button>
					<Alert.Root status="warning" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>Chapter not found.</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				</Container>
			</Box>
		);
	}

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Stack gap={6}>
					<ChapterHeaderCard
						work={work}
						chapter={chapter}
						promptMeta={promptMeta}
						promptDrawerTrigger={promptDrawerTrigger}
						onRegenerateSegments={onRegenerateSegments}
						isRegeneratingSegments={isRegeneratingSegments}
						onNavigateBack={onNavigateBack}
					/>

					<ChapterNavigation
						nextId={chapter.next_chapter_id}
						prevId={chapter.prev_chapter_id}
						onNavigate={onNavigateChapter}
					/>

					<TranslationPanel {...translationPanelProps} />

					<ChapterNavigation
						nextId={chapter.next_chapter_id}
						prevId={chapter.prev_chapter_id}
						onNavigate={onNavigateChapter}
					/>
				</Stack>
			</Container>
		</Box>
	);
}
