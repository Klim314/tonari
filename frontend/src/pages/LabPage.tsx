import {
	Box,
	Button,
	Container,
	HStack,
	Heading,
	Spinner,
	Text,
	Textarea,
	VStack,
} from "@chakra-ui/react";
import { useCallback, useState } from "react";
import { client } from "../client/client.gen";
import { LabLane, type LabLaneConfig } from "../components/Lab/LabLane";
import { useModels } from "../hooks/useModels";

export function LabPage() {
	const [inputText, setInputText] = useState("");
	const { data: availableModels, loading: modelsLoading } = useModels();

	const [lanes, setLanes] = useState<LabLaneConfig[]>([
		{
			id: crypto.randomUUID(),
			model: "gpt-4o",
			template: "Translate the following to English.",
			status: "idle",
			output: "",
		},
		{
			id: crypto.randomUUID(),
			model: "claude-3-5-sonnet",
			template: "Translate the following to English.",
			status: "idle",
			output: "",
		},
	]);

	const handleAddLane = useCallback(() => {
		setLanes((prev) => [
			...prev,
			{
				id: crypto.randomUUID(),
				model: "gpt-4o",
				template: "Translate the following to English.",
				status: "idle",
				output: "",
			},
		]);
	}, []);

	const handleRemoveLane = useCallback((id: string) => {
		setLanes((prev) => prev.filter((l) => l.id !== id));
	}, []);

	const handleConfigChange = useCallback(
		(id: string, updates: Partial<LabLaneConfig>) => {
			setLanes((prev) =>
				prev.map((l) => (l.id === id ? { ...l, ...updates } : l)),
			);
		},
		[],
	);

	// Re-implementing run logic with raw fetch for text/plain streaming
	const runAll = async () => {
		if (!inputText.trim()) return;

		// Trigger all
		for (const lane of lanes) {
			handleConfigChange(lane.id, {
				status: "running",
				output: "",
				error: undefined,
			});
			streamLane(lane.id, inputText);
		}
	};

	const streamLane = async (laneId: string, text: string) => {
		const lane = lanes.find((l) => l.id === laneId);
		if (!lane) {
			return;
		}

		const startTime = Date.now();

		try {
			// Construct URL using client config base URL
			const baseUrl = client.getConfig().baseURL || "";

			const response = await fetch(`${baseUrl}/lab/stream`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					text: text,
					model: lane.model,
					template: lane.template,
					params: {},
				}),
			});

			if (!response.ok) {
				const errText = await response.text().catch(() => response.statusText);
				throw new Error(errText || `Error ${response.status}`);
			}

			if (!response.body) throw new Error("No response body");

			const reader = response.body.getReader();
			const decoder = new TextDecoder();

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value, { stream: true });
				setLanes((prev) => {
					return prev.map((l) =>
						l.id === laneId ? { ...l, output: l.output + chunk } : l,
					);
				});
			}

			const duration = Date.now() - startTime;
			handleConfigChange(laneId, {
				status: "completed",
				metrics: { durationMs: duration },
			});
		} catch (err: unknown) {
			const errorMessage = err instanceof Error ? err.message : String(err);
			handleConfigChange(laneId, { status: "error", error: errorMessage });
		}
	};

	if (modelsLoading && lanes.length === 0) {
		return (
			<Container centerContent p={10}>
				<Spinner size="xl" />
			</Container>
		);
	}

	return (
		<Container maxW="100%" h="calc(100vh - 64px)" p={0} display="flex" flexDirection="column" bg="white">
			{/* Top Bar */}
			<HStack p={4} borderBottomWidth="1px" borderColor="gray.200" justify="space-between" bg="gray.50">
				<VStack align="start" gap={0}>
					<Heading size="md" color="gray.800">Prompt Lab</Heading>
					<Text fontSize="xs" color="gray.500">Compare prompt outputs side-by-side</Text>
				</VStack>
				<HStack>
					<Button size="sm" onClick={handleAddLane} variant="outline" colorPalette="gray">Add Lane</Button>
					<Button size="sm" colorPalette="blue" onClick={runAll} loading={lanes.some(l => l.status === "running")}>
						Run All
					</Button>
				</HStack>
			</HStack>

			{/* Main Content Area */}
			<HStack flex="1" align="stretch" overflow="hidden" gap={0}>
				{/* Input Panel (Left) */}
				<Box w="300px" borderRightWidth="1px" borderColor="gray.200" p={4} bg="white" display="flex" flexDirection="column" gap={4}>
					<Heading size="sm" color="gray.700">Input Text</Heading>
					<Textarea
						flex="1"
						placeholder="Enter Japanese text here..."
						value={inputText}
						onChange={(e) => setInputText(e.target.value)}
						resize="none"
						bg="white"
						borderColor="gray.200"
						_focus={{ ring: 1, ringColor: "blue.500", borderColor: "blue.500" }}
						color="gray.800"
					/>
				</Box>

				{/* Lanes Area (Right - Horizontal Scroll) */}
				<Box flex="1" overflowX="auto" overflowY="hidden" p={4} bg="gray.50">
					<HStack h="100%" align="stretch" gap={4} minW="min-content">
						{lanes.map((lane) => (
							<LabLane
								key={lane.id}
								config={lane}
								onConfigChange={handleConfigChange}
								onRemove={handleRemoveLane}
								models={availableModels}
							/>
						))}
					</HStack>
				</Box>
			</HStack>
		</Container>
	);
}
