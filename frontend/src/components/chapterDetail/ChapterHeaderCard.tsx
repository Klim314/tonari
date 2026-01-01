import {
	Badge,
	Box,
	Button,
	HStack,
	Heading,
	Icon,
	Menu,
	Separator,
	Stack,
	Text,
} from "@chakra-ui/react";
import { ArrowLeft, Settings } from "lucide-react";
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
	onNavigateBack,
}: ChapterHeaderCardProps & { onNavigateBack: () => void }) {
	return (
		<Box borderWidth="1px" borderRadius="lg" bg="white" shadow="sm">
			{/* Top Section: Title & Menu */}
			<Box p={5} pb={3}>
				<HStack justify="space-between" align="flex-start">
					<Stack gap={1}>
						<HStack gap={2} align="center" color="gray.500">
							<Button
								variant="ghost"
								size="xs"
								p={0}
								minW={6}
								h={6}
								onClick={onNavigateBack}
								color="gray.400"
								_hover={{ color: "gray.700", bg: "gray.100" }}
							>
								<Icon as={ArrowLeft} boxSize={4} />
							</Button>
							<Text fontSize="sm" fontWeight="medium">
								{work.title}
							</Text>
						</HStack>
						<Heading size="lg" ml={8}>
							Chapter {formatChapterKey(chapter.idx)}: {chapter.title}
						</Heading>
					</Stack>

					<Menu.Root positioning={{ placement: "bottom-end" }}>
						<Menu.Trigger asChild>
							<Button variant="ghost" size="sm" color="gray.400">
								<Icon as={Settings} boxSize={5} />
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
				</HStack>
			</Box>

			<Separator />

			{/* Meta Section */}
			<Box p={4} bg="gray.50" borderBottomRadius="lg">
				<Stack
					direction={{ base: "column", md: "row" }}
					gap={4}
					align={{ base: "flex-start", md: "center" }}
					justify="space-between"
				>
					<HStack gap={3} flexWrap="wrap">
						<Badge variant="surface" colorPalette="gray">
							Sort: {chapter.sort_key.toFixed(1)}
						</Badge>

						{promptMeta.isDirty ? (
							<Badge colorPalette="yellow">Unsaved Override</Badge>
						) : (
							<Badge colorPalette="blue" variant="outline">Saved Prompt</Badge>
						)}
						{promptMeta.notAssigned && (
							<Badge colorPalette="orange">No Prompt</Badge>
						)}
						{promptMeta.error && (
							<Badge colorPalette="red">Error</Badge>
						)}

						<Text fontSize="xs" color="gray.500" borderLeftWidth="1px" pl={3} ml={1}>
							{promptMeta.loading
								? "Loading..."
								: promptMeta.promptName || "System Default"}
						</Text>
					</HStack>

					{promptDrawerTrigger}
				</Stack>
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
