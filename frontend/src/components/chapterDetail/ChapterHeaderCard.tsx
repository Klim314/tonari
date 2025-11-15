import {
	Badge,
	Box,
	Button,
	HStack,
	Heading,
	Icon,
	Menu,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Settings } from "lucide-react";
import type { ReactNode } from "react";
import type { Chapter, Work } from "../../types/works";
import type { PromptMeta } from "./types";

interface ChapterHeaderCardProps {
	work: Work;
	chapter: Chapter;
	promptMeta: PromptMeta;
	promptDrawerTrigger: ReactNode;
	onRegenerateSegments: () => void;
	isRegeneratingSegments: boolean;
}

export function ChapterHeaderCard({
	work,
	chapter,
	promptMeta,
	promptDrawerTrigger,
	onRegenerateSegments,
	isRegeneratingSegments,
}: ChapterHeaderCardProps) {
	return (
		<Box borderWidth="1px" borderRadius="lg" p={6} position="relative">
			<Text color="gray.400" fontSize="sm" mb={2}>
				{work.title}
			</Text>
			<Heading size="lg" mb={2}>
				Chapter {formatChapterKey(chapter.idx)}: {chapter.title}
			</Heading>
			<Stack
				direction={{ base: "column", md: "row" }}
				gap={3}
				align={{ base: "flex-start", md: "center" }}
				justify="space-between"
				mb={4}
			>
				<Text color="gray.400" fontSize="sm">
					Sort key {chapter.sort_key.toFixed(4)}
				</Text>
				<HStack gap={2} flexWrap="wrap">
					{promptMeta.isDirty ? (
						<Badge colorPalette="yellow">Using unsaved override</Badge>
					) : (
						<Badge colorPalette="gray">Using saved prompt</Badge>
					)}
					{promptMeta.notAssigned ? (
						<Badge colorPalette="orange">Assign a prompt to save changes</Badge>
					) : null}
					{promptMeta.error ? (
						<Badge colorPalette="red">Prompt load failed</Badge>
					) : null}
					<Text fontSize="sm" color="gray.500">
						{promptMeta.loading
							? "Loading prompt..."
							: promptMeta.promptName
								? `Prompt: ${promptMeta.promptName}`
								: promptMeta.notAssigned
									? "No prompt assigned to this work."
									: "Prompt: Default system prompt"}
					</Text>
				</HStack>
				{promptDrawerTrigger}
			</Stack>

			<Box position="absolute" top={4} right={4}>
				<Menu.Root positioning={{ placement: "bottom-end" }}>
					<Menu.Trigger asChild>
						<Button variant="outline" size="sm">
							<Icon as={Settings} boxSize={4} />
						</Button>
					</Menu.Trigger>
					<Menu.Positioner>
						<Menu.Content>
							<Menu.Item
								value="regenerate-segments"
								onClick={onRegenerateSegments}
								disabled={isRegeneratingSegments}
							>
								Regenerate Segments
							</Menu.Item>
						</Menu.Content>
					</Menu.Positioner>
				</Menu.Root>
			</Box>
		</Box>
	);
}

function formatChapterKey(key: Chapter["idx"]) {
	if (typeof key === "number") {
		return Number.isInteger(key) ? String(key) : key.toFixed(2);
	}
	return key;
}
