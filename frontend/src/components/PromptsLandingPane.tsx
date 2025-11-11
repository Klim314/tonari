import { Box, Container, Heading, Stack, Text } from "@chakra-ui/react";

export function PromptsLandingPane() {
	return (
		<Container maxW="6xl">
			<Stack direction={{ base: "column", lg: "row" }} gap={6}>
				<Box
					flex="1"
					borderWidth="1px"
					borderColor="whiteAlpha.200"
					borderRadius="md"
					p={6}
					minH="400px"
				>
					<Heading size="md" mb={4}>
						Prompt Filters
					</Heading>
					<Text color="gray.400" fontSize="sm">
						Filter rail coming soon: search, tags, owner dropdowns, recent
						prompts list.
					</Text>
				</Box>

				<Box
					flex="2"
					borderWidth="1px"
					borderColor="whiteAlpha.200"
					borderRadius="md"
					p={6}
					minH="400px"
				>
					<Heading size="md" mb={4}>
						Prompt Detail / Editor
					</Heading>
					<Text color="gray.400" fontSize="sm" mb={4}>
						Detail and editor pane coming soon: title field, metadata chips,
						body editor/preview, action buttons for sharing and duplicating.
					</Text>
					<Box
						borderWidth="1px"
						borderColor="whiteAlpha.100"
						borderRadius="md"
						p={4}
						bg="whiteAlpha.50"
					>
						<Text fontSize="xs" color="gray.500">
							This placeholder matches the design spec from the landing page
							revamp plan. Backend endpoints and UI components will be added in
							future iterations.
						</Text>
					</Box>
				</Box>
			</Stack>
		</Container>
	);
}
