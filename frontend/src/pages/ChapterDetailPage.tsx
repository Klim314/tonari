import {
	Alert,
	Box,
	Button,
	Container,
	Heading,
	Separator,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { useChapter } from "../hooks/useChapter";
import { useWork } from "../hooks/useWork";
import type { Chapter } from "../types/works";

interface ChapterDetailPageProps {
	workId: number;
	chapterId: number;
	onNavigateBack: (path?: string) => void;
}

export function ChapterDetailPage({
	workId,
	chapterId,
	onNavigateBack,
}: ChapterDetailPageProps) {
	const {
		data: work,
		loading: workLoading,
		error: workError,
	} = useWork(workId);
	const {
		data: chapter,
		loading: chapterLoading,
		error: chapterError,
	} = useChapter(workId, chapterId);

	const loading = workLoading || chapterLoading;
	const error = workError || chapterError;

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Button
					variant="ghost"
					mb={4}
					onClick={() => onNavigateBack(`/works/${workId}`)}
				>
					← Back to work
				</Button>

				{loading ? (
					<Stack spacing={4}>
						<Skeleton height="32px" borderRadius="md" />
						<Skeleton height="420px" borderRadius="lg" />
					</Stack>
				) : error ? (
					<Alert.Root status="error" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Failed to load chapter: {error}
							</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : !work || !chapter ? (
					<Alert.Root status="warning" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>Chapter not found.</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : (
					<Stack spacing={8}>
						<Box borderWidth="1px" borderRadius="lg" p={6}>
							<Text color="gray.400" fontSize="sm" mb={2}>
								{work.title}
							</Text>
							<Heading size="lg" mb={2}>
								Chapter {formatChapterKey(chapter.idx)}: {chapter.title}
							</Heading>
							<Text color="gray.400" fontSize="sm">
								Sort key {chapter.sort_key.toFixed(4)}
							</Text>
						</Box>

						<Stack
							direction={{ base: "column", lg: "row" }}
							spacing={8}
							align="flex-start"
						>
							<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
								<Heading size="md" mb={4}>
									Source Text
								</Heading>
								<Separator mb={4} />
								<Text
									whiteSpace="pre-wrap"
									fontFamily="mono"
									lineHeight="tall"
									color="gray.100"
								>
									{chapter.normalized_text}
								</Text>
							</Box>

							<Box flex="1" w="full" borderWidth="1px" borderRadius="lg" p={6}>
								<Heading size="md" mb={4}>
									Translation (coming soon)
								</Heading>
								<Separator mb={4} />
								<Text color="gray.400">
									Aligned translation segments will appear here once the
									translation service is implemented. For now, use this space to
									plan how you want the bilingual view to look.
								</Text>
							</Box>
						</Stack>
					</Stack>
				)}
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
