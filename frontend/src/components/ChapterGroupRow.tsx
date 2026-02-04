import {
	Box,
	Button,
	Badge,
	Collapsible,
	HStack,
	Icon,
	Spinner,
	Stack,
	Text,
} from "@chakra-ui/react";
import { ChevronDown, ChevronRight, Folder, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

// Placeholder types - will be replaced with generated API types
interface ChapterGroupMember {
	id: number;
	chapter_id: number;
	order_index: number;
	chapter: {
		id: number;
		idx: number;
		title: string;
		sort_key: string;
		is_fully_translated?: boolean;
	};
}

interface ChapterGroupDetail {
	id: number;
	work_id: number;
	name: string;
	created_at: string;
	updated_at: string;
	member_count: number;
	min_sort_key: number;
	item_type: "group";
	is_fully_translated?: boolean;
	members?: ChapterGroupMember[];
}

interface ChapterGroupRowProps {
	group: ChapterGroupDetail;
	onNavigateToChapter?: (chapterId: number) => void;
	onDelete?: () => void;
	manageMode?: boolean;
}

function formatChapterKey(idx: number): string {
	return idx.toString();
}

export function ChapterGroupRow({
	group,
	onNavigateToChapter,
	onDelete,
	manageMode = false,
}: ChapterGroupRowProps) {
	const [isExpanded, setIsExpanded] = useState(false);
	const [members, setMembers] = useState<ChapterGroupMember[] | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const fetchMembers = useCallback(async () => {
		if (members !== null) return; // Already fetched

		setLoading(true);
		setError(null);

		try {
			const response = await fetch(
				`/api/works/${group.work_id}/chapter-groups/${group.id}`,
			);
			if (!response.ok) {
				throw new Error("Failed to load group details");
			}
			const data = await response.json();
			setMembers(data.members || []);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load");
		} finally {
			setLoading(false);
		}
	}, [group.work_id, group.id, members]);

	// Fetch members when expanded
	useEffect(() => {
		if (isExpanded && members === null && !loading) {
			fetchMembers();
		}
	}, [isExpanded, members, loading, fetchMembers]);

	return (
		<Collapsible.Root
			open={isExpanded}
			onOpenChange={(e) => setIsExpanded(e.open)}
		>
			<Box
				borderWidth="1px"
				borderRadius="md"
				borderLeftWidth="3px"
				borderLeftColor="teal.500"
			>
				{/* Group Header */}
				<HStack
					p={4}
					cursor="pointer"
					transition="background-color 0.2s ease"
					_hover={{ bg: "gray.800" }}
				>
					<Collapsible.Trigger asChild>
						<HStack flex="1" gap={3}>
							<Icon as={isExpanded ? ChevronDown : ChevronRight} boxSize={5} />
							<Icon as={Folder} boxSize={5} color="teal.400" />
							<Box flex="1">
								<HStack gap={2}>
									<Text fontWeight="semibold" color="teal.200">
										{group.name}
									</Text>
									{group.is_fully_translated && (
										<Badge colorPalette="green" variant="subtle">
											Translated
										</Badge>
									)}
									<Text fontSize="sm" color="gray.400">
										({group.member_count}{" "}
										{group.member_count === 1 ? "chapter" : "chapters"})
									</Text>
								</HStack>
							</Box>
						</HStack>
					</Collapsible.Trigger>

					{manageMode && onDelete && (
						<Button
							size="sm"
							variant="ghost"
							colorPalette="red"
							onClick={(e) => {
								e.stopPropagation();
								onDelete();
							}}
							title="Delete group"
						>
							<Icon as={Trash2} boxSize={4} />
						</Button>
					)}
				</HStack>

				{/* Expandable Content - Member Chapters */}
				<Collapsible.Content>
					<Stack gap={2} px={4} pb={4} borderTopWidth="1px" pt={4}>
						{loading ? (
							<HStack justify="center" py={4}>
								<Spinner size="sm" />
								<Text color="gray.400" fontSize="sm">
									Loading chapters...
								</Text>
							</HStack>
						) : error ? (
							<Text color="red.400" fontSize="sm" ml={8}>
								{error}
							</Text>
						) : members && members.length > 0 ? (
							members
								.sort((a, b) => a.order_index - b.order_index)
								.map((member) => (
									<Box
										key={member.id}
										borderWidth="1px"
										borderRadius="md"
										p={3}
										as={onNavigateToChapter ? "button" : "div"}
										textAlign="left"
										cursor={onNavigateToChapter ? "pointer" : "default"}
										transition="background-color 0.2s ease"
										_hover={
											onNavigateToChapter ? { bg: "gray.800" } : undefined
										}
										onClick={
											onNavigateToChapter
												? () => onNavigateToChapter(member.chapter_id)
												: undefined
										}
										ml={6}
									>
										<HStack justify="space-between" mb={1}>
											<Text fontWeight="medium" color="teal.200" fontSize="sm">
												Chapter {formatChapterKey(member.chapter.idx)}
											</Text>
											{member.chapter.is_fully_translated && (
												<Badge colorPalette="green" variant="subtle" size="xs">
													Translated
												</Badge>
											)}
										</HStack>
										<Text fontSize="sm">{member.chapter.title}</Text>
									</Box>
								))
						) : (
							<Text color="gray.500" fontSize="sm" ml={6}>
								No chapters in this group
							</Text>
						)}
					</Stack>
				</Collapsible.Content>
			</Box>
		</Collapsible.Root>
	);
}
