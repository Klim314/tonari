import {
	Alert,
	Box,
	Button,
	Container,
	Skeleton,
	Stack,
} from "@chakra-ui/react";
import type { ReactNode } from "react";
import type { Chapter, Work } from "../../types/works";
import { ChapterHeaderCard } from "./ChapterHeaderCard";
import { SourceTextPanel } from "./SourceTextPanel";
import { TranslationPanel } from "./translation/TranslationPanel";
import type { TranslationPanelProps } from "./translation/TranslationPanel";
import type { PromptMeta } from "./types";

export interface ChapterDetailViewProps {
	work: Work | null;
	chapter: Chapter | null;
	promptMeta: PromptMeta;
	promptDrawerTrigger: ReactNode;
	translationPanelProps: TranslationPanelProps;
	onNavigateBack: () => void;
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
				<Button variant="ghost" mb={4} onClick={onNavigateBack}>
					← Back to work
				</Button>

				<Stack gap={8}>
					<ChapterHeaderCard
						work={work}
						chapter={chapter}
						promptMeta={promptMeta}
						promptDrawerTrigger={promptDrawerTrigger}
						onRegenerateSegments={onRegenerateSegments}
						isRegeneratingSegments={isRegeneratingSegments}
					/>

					<Stack
						direction={{ base: "column", lg: "row" }}
						gap={8}
						align="flex-start"
					>
						<SourceTextPanel text={chapter.normalized_text} />
						<TranslationPanel {...translationPanelProps} />
					</Stack>
				</Stack>
			</Container>
		</Box>
	);
}
