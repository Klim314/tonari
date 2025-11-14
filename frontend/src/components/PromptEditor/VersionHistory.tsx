import { Badge, Button, HStack, Heading, Text, VStack } from "@chakra-ui/react";
import type { PromptVersionOut } from "../../client";

interface VersionHistoryProps {
	versions: PromptVersionOut[];
	selectedVersionId: number | null;
	latestVersionId: number | undefined;
	onSelectVersion: (versionId: number) => void;
}

function formatTimeAgo(date: string | Date): string {
	const d = new Date(date);
	const now = new Date();
	const seconds = Math.floor((now.getTime() - d.getTime()) / 1000);

	if (seconds < 60) return `${seconds}s ago`;
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days < 30) return `${days}d ago`;
	const months = Math.floor(days / 30);
	if (months < 12) return `${months}mo ago`;
	const years = Math.floor(months / 12);
	return `${years}y ago`;
}

export function VersionHistory({
	versions,
	selectedVersionId,
	latestVersionId,
	onSelectVersion,
}: VersionHistoryProps) {
	// Sort versions in descending order (newest first)
	const sortedVersions = [...versions].sort(
		(a, b) => b.version_number - a.version_number,
	);

	return (
		<VStack align="stretch" gap={3} h="100%">
			<Heading size="sm">Version History</Heading>

			<VStack align="stretch" gap={2} flex="1" overflowY="auto">
				{sortedVersions.length === 0 ? (
					<Text color="gray.400" fontSize="sm">
						No versions yet
					</Text>
				) : (
					sortedVersions.map((version) => {
						const isSelected = selectedVersionId === version.id;
						const isLatest = version.id === latestVersionId;

						return (
							<Button
								key={version.id}
								size="sm"
								variant={isSelected ? "solid" : "ghost"}
								colorScheme={isSelected ? "blue" : undefined}
								width="100%"
								height="auto"
								py={3}
								px={3}
								justifyContent="flex-start"
								textAlign="left"
								whiteSpace="normal"
								onClick={() => onSelectVersion(version.id)}
								borderWidth="1px"
								borderColor={
									isSelected
										? "blue.400"
										: isLatest
											? "blue.200"
											: "whiteAlpha.100"
								}
								borderRadius="md"
								_hover={{
									borderColor: isSelected ? "blue.400" : "blue.300",
									bg: isSelected ? undefined : "whiteAlpha.50",
								}}
							>
								<VStack align="stretch" gap={1} width="100%">
									<HStack justify="space-between" gap={2}>
										<Text fontWeight="600" fontSize="sm">
											v{version.version_number}
										</Text>
										{isLatest && (
											<Badge size="sm" colorScheme="blue">
												Latest
											</Badge>
										)}
										{isSelected && (
											<Text fontSize="xs" color="blue.200">
												✓
											</Text>
										)}
									</HStack>

									<Text fontSize="xs" color="gray.400">
										{version.model}
									</Text>

									<Text fontSize="xs" color="gray.500">
										{formatTimeAgo(version.created_at)}
									</Text>
								</VStack>
							</Button>
						);
					})
				)}
			</VStack>
		</VStack>
	);
}
