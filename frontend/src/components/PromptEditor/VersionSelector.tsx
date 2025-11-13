import { Button, Menu, HStack, Text } from "@chakra-ui/react";
import type { PromptVersionOut } from "../../client";

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

interface VersionSelectorProps {
	versions: PromptVersionOut[];
	selectedVersionId: number | null;
	latestVersionId: number | undefined;
	onSelectVersion: (versionId: number) => void;
}

export function VersionSelector({
	versions,
	selectedVersionId,
	latestVersionId,
	onSelectVersion,
}: VersionSelectorProps) {
	const sortedVersions = [...versions].sort((a, b) => b.version_number - a.version_number);
	const selectedVersion = selectedVersionId
		? sortedVersions.find((v) => v.id === selectedVersionId)
		: sortedVersions[0];

	if (sortedVersions.length === 0) {
		return <Text fontSize="sm" color="gray.500">No versions yet</Text>;
	}

	return (
		<Menu.Root>
			<Menu.Trigger asChild>
				<Button size="sm" variant="outline" whiteSpace="nowrap">
					v{selectedVersion?.version_number || "—"} ▼
				</Button>
			</Menu.Trigger>
			<Menu.Positioner>
				<Menu.Content maxH="300px" overflowY="auto" minW="350px">
					{sortedVersions.map((version) => (
						<Menu.Item
							key={version.id}
							value={version.id.toString()}
							onClick={() => onSelectVersion(version.id)}
							fontSize="sm"
						>
							<HStack gap={2} justify="space-between" width="100%">
								<Text whiteSpace="nowrap">
									v{version.version_number} • {version.model}
									{version.id === latestVersionId && " (latest)"}
								</Text>
								<Text fontSize="xs" color="gray.500" whiteSpace="nowrap">
									{formatTimeAgo(version.created_at)}
								</Text>
							</HStack>
						</Menu.Item>
					))}
				</Menu.Content>
			</Menu.Positioner>
		</Menu.Root>
	);
}
