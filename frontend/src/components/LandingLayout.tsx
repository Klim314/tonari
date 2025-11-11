import {
	Box,
	Button,
	Container,
	HStack,
	Heading,
	Stack,
} from "@chakra-ui/react";
import type { ReactNode } from "react";

export type Domain = "works" | "prompts";

interface LandingLayoutProps {
	activeDomain: Domain;
	onDomainChange: (domain: Domain) => void;
	onNewWork?: () => void;
	children: ReactNode;
}

export function LandingLayout({
	activeDomain,
	onDomainChange,
	onNewWork,
	children,
}: LandingLayoutProps) {
	return (
		<Box minH="100vh" bg="white">
			<Box
				borderBottomWidth="1px"
				borderColor="gray.200"
				bg="gray.50"
				position="sticky"
				top={0}
				zIndex={10}
				boxShadow="sm"
			>
				<Container maxW="6xl">
					<Stack
						direction={{ base: "column", md: "row" }}
						justify="space-between"
						align={{ base: "flex-start", md: "center" }}
						py={4}
						gap={4}
					>
						<HStack gap={6} flex="1">
							<Heading size="lg" fontWeight="bold" color="gray.800">
								Tonari
							</Heading>
							<HStack
								gap={0}
								borderWidth="1px"
								borderColor="gray.300"
								borderRadius="md"
								overflow="hidden"
								bg="white"
							>
								<Button
									variant={activeDomain === "works" ? "solid" : "ghost"}
									colorScheme={activeDomain === "works" ? "teal" : "gray"}
									borderRadius={0}
									onClick={() => onDomainChange("works")}
									size="sm"
								>
									Works
								</Button>
								<Button
									variant={activeDomain === "prompts" ? "solid" : "ghost"}
									colorScheme={activeDomain === "prompts" ? "teal" : "gray"}
									borderRadius={0}
									onClick={() => onDomainChange("prompts")}
									size="sm"
								>
									Prompts
								</Button>
							</HStack>
						</HStack>

						{activeDomain === "works" && onNewWork && (
							<Button colorScheme="teal" size="sm" onClick={onNewWork}>
								+ New Work
							</Button>
						)}
					</Stack>
				</Container>
			</Box>

			<Box py={8}>{children}</Box>
		</Box>
	);
}
