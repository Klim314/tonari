import {
	Box,
	Button,
	Container,
	Heading,
	Icon,
	Input,
	SimpleGrid,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { type ComponentProps, useState } from "react";
import { AddWorkModal } from "../components/AddWorkModal";
import { WorkCard } from "../components/WorkCard";
import { useWorks } from "../hooks/useWorks";

const SearchIcon = (props: ComponentProps<typeof Icon>) => (
	<Icon viewBox="0 0 24 24" {...props}>
		<path
			fill="currentColor"
			d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.71.71l.27.28v.79l4.25 4.25a1 1 0 0 0 1.42-1.42L15.5 14Zm-6 0A4.5 4.5 0 1 1 10 5a4.5 4.5 0 0 1-.5 9Z"
		/>
	</Icon>
);

interface WorksPageProps {
	onSelectWork?: (workId: number) => void;
}

export function WorksPage({ onSelectWork }: WorksPageProps) {
	const [query, setQuery] = useState("");
	const [refreshToken, setRefreshToken] = useState(0);
	const [isAddModalOpen, setAddModalOpen] = useState(false);
	const { data, loading, error } = useWorks(query, refreshToken);

	const works = data?.items ?? [];
	const handleImportSuccess = () => {
		setRefreshToken((token) => token + 1);
	};

	return (
		<Box py={10}>
			<Container maxW="6xl">
				<Stack spacing={6}>
					<Stack
						spacing={4}
						direction={{ base: "column", md: "row" }}
						justify="space-between"
						align={{ base: "flex-start", md: "center" }}
					>
						<Stack spacing={2}>
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
							<SearchIcon color="gray.500" />
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
								? Array.from({ length: 6 }).map((_, index) => (
										<Skeleton key={index} height="120px" borderRadius="md" />
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
