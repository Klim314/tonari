import {
	Box,
	Button,
	Container,
	Heading,
	Input,
	SimpleGrid,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Search } from "lucide-react";
import { useState } from "react";
import { AddWorkModal } from "../components/AddWorkModal";
import { WorkCard } from "../components/WorkCard";
import { useWorks } from "../hooks/useWorks";

interface WorksPageProps {
	onSelectWork?: (workId: number) => void;
}

export function WorksPage({ onSelectWork }: WorksPageProps) {
	const [query, setQuery] = useState("");
	const [refreshToken, setRefreshToken] = useState(0);
	const [isAddModalOpen, setAddModalOpen] = useState(false);
	const { data, loading, error } = useWorks(query, refreshToken);

	const works = data?.items ?? [];
	const skeletonKeys = ["one", "two", "three", "four", "five", "six"];
	const handleImportSuccess = () => {
		setRefreshToken((token) => token + 1);
	};

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Stack gap={6}>
					<Stack
						gap={4}
						direction={{ base: "column", md: "row" }}
						justify="space-between"
						align={{ base: "flex-start", md: "center" }}
					>
						<Stack gap={2}>
							<Heading size="lg">Works</Heading>
							<Text color="gray.400">
								Showing {works.length} of {data?.total ?? 0} tracked works.
							</Text>
						</Stack>
						<Button colorScheme="teal" onClick={() => setAddModalOpen(true)}>
							Add New Work
						</Button>
					</Stack>

					<Box maxW="lg" position="relative">
						<Box
							position="absolute"
							left="3"
							top="50%"
							transform="translateY(-50%)"
							pointerEvents="none"
						>
							<Search size={18} color="var(--chakra-colors-gray-500)" />
						</Box>
						<Input
							pl="10"
							value={query}
							onChange={(event) => setQuery(event.target.value)}
							placeholder="Search works by title"
							borderColor="whiteAlpha.200"
						/>
					</Box>

					{error ? (
						<Box
							borderWidth="1px"
							borderColor="whiteAlpha.200"
							borderRadius="md"
							p={6}
						>
							<Text color="red.300">Failed to load works: {error}</Text>
						</Box>
					) : (
						<SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} gap={6}>
							{loading
								? skeletonKeys.map((key) => (
										<Skeleton
											key={`works-skeleton-${key}`}
											height="120px"
											borderRadius="md"
										/>
									))
								: works.map((work) => (
										<WorkCard
											key={work.id}
											work={work}
											onSelect={onSelectWork}
											href={`/works/${work.id}`}
										/>
									))}
						</SimpleGrid>
					)}
				</Stack>
			</Container>
			<AddWorkModal
				isOpen={isAddModalOpen}
				onClose={() => setAddModalOpen(false)}
				onImported={handleImportSuccess}
			/>
		</Box>
	);
}
