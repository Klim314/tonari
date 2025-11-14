import {
	Alert,
	Box,
	Container,
	HStack,
	Heading,
	Input,
	SimpleGrid,
	Skeleton,
	Stack,
	Text,
} from "@chakra-ui/react";
import { Search } from "lucide-react";
import { useState } from "react";
import { useWorks } from "../hooks/useWorks";
import { WorkCard } from "./WorkCard";

interface LandingWorksPaneProps {
	onSelectWork: (workId: number) => void;
}

export function LandingWorksPane({ onSelectWork }: LandingWorksPaneProps) {
	const [query, setQuery] = useState("");
	const { data, loading, error } = useWorks(query, 0);

	const works = data?.items ?? [];

	return (
		<Container maxW="6xl">
			<Stack gap={6}>
				<Stack gap={4}>
					<HStack justify="space-between" align="center">
						<Heading size="lg" color="gray.800">
							Works
						</Heading>
						<Text color="gray.600">
							Showing {works.length} of {data?.total ?? 0} tracked works
						</Text>
					</HStack>

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
							borderWidth="2px"
							borderColor="gray.300"
							bg="white"
							_hover={{ borderColor: "gray.400" }}
							_focus={{
								borderColor: "teal.500",
								boxShadow: "0 0 0 1px var(--chakra-colors-teal-500)",
							}}
						/>
					</Box>
				</Stack>

				{error ? (
					<Alert.Root status="error" borderRadius="md">
						<Alert.Indicator />
						<Alert.Content>
							<Alert.Description>
								Failed to load works: {error}
							</Alert.Description>
						</Alert.Content>
					</Alert.Root>
				) : loading ? (
					<SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} gap={6}>
						{[1, 2, 3, 4, 5, 6].map((key) => (
							<Skeleton key={key} height="120px" borderRadius="md" />
						))}
					</SimpleGrid>
				) : works.length === 0 ? (
					<Box
						borderWidth="1px"
						borderRadius="md"
						p={8}
						borderColor="gray.200"
						bg="gray.50"
					>
						<Text color="gray.600" textAlign="center">
							No works found.
						</Text>
					</Box>
				) : (
					<SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} gap={6}>
						{works.map((work) => (
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
	);
}
