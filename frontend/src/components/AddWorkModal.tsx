import {
	AlertContent,
	AlertDescription,
	AlertIndicator,
	AlertRoot,
	Box,
	Button,
	DialogBackdrop,
	DialogBody,
	DialogCloseTrigger,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogPositioner,
	DialogRoot,
	DialogTitle,
	FieldHelperText,
	FieldLabel,
	FieldRoot,
	HStack,
	Icon,
	Stack,
	Text,
	Textarea,
} from "@chakra-ui/react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Works } from "../client";
import { getApiErrorMessage } from "../lib/api";

interface AddWorkModalProps {
	isOpen: boolean;
	onClose: () => void;
	onImported: (count: number) => void;
}

type ImportResult = {
	url: string;
	status: "success" | "error";
	message?: string;
};

const parseUrls = (value: string) =>
	value
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter((line) => line.length > 0);

export function AddWorkModal({
	isOpen,
	onClose,
	onImported,
}: AddWorkModalProps) {
	const [inputValue, setInputValue] = useState("");
	const [submitting, setSubmitting] = useState(false);
	const [results, setResults] = useState<ImportResult[]>([]);
	const [formError, setFormError] = useState<string | null>(null);

	const urls = useMemo(() => parseUrls(inputValue), [inputValue]);
	const hasUrls = urls.length > 0;

	useEffect(() => {
		if (!isOpen) {
			setInputValue("");
			setSubmitting(false);
			setResults([]);
			setFormError(null);
		}
	}, [isOpen]);

	const handleSubmit = async () => {
		if (!hasUrls) {
			setFormError("Enter at least one URL to import.");
			return;
		}
		setFormError(null);
		setSubmitting(true);
		setResults([]);

		const newResults: ImportResult[] = [];
		let successCount = 0;

		for (const url of urls) {
			try {
				await Works.importWorkWorksImportPost({
					body: { url, force: false },
					throwOnError: true,
				});
				newResults.push({ url, status: "success" });
				successCount += 1;
			} catch (error) {
				const message = getApiErrorMessage(error, "Failed to import work.");
				newResults.push({ url, status: "error", message });
			}
		}

		setResults(newResults);
		setSubmitting(false);
		if (successCount > 0) {
			onImported(successCount);
		}
	};

	const resultSummary = results.length
		? {
				success: results.filter((r) => r.status === "success").length,
				failed: results.filter((r) => r.status === "error").length,
			}
		: null;

	return (
		<DialogRoot
			open={isOpen}
			onOpenChange={(details) => {
				if (!details.open) {
					onClose();
				}
			}}
			lazyMount
			unmountOnExit
		>
			<DialogBackdrop />
			<DialogPositioner>
				<DialogContent>
					<DialogCloseTrigger />
					<DialogHeader>
						<DialogTitle>Add New Work</DialogTitle>
					</DialogHeader>
					<DialogBody>
						<Stack gap={4}>
							<FieldRoot required>
								<FieldLabel htmlFor="work-urls-input">Work URLs</FieldLabel>
								<Textarea
									id="work-urls-input"
									placeholder="Paste one URL per line"
									minH="140px"
									value={inputValue}
									onChange={(event) => setInputValue(event.target.value)}
									isDisabled={submitting}
								/>
								<FieldHelperText>
									Supports multiple URLs. Each URL will be imported in sequence.
								</FieldHelperText>
							</FieldRoot>

							{formError ? (
								<AlertRoot status="warning">
									<AlertIndicator />
									<AlertContent>
										<AlertDescription>{formError}</AlertDescription>
									</AlertContent>
								</AlertRoot>
							) : null}

							{resultSummary ? (
								<Box
									borderWidth="1px"
									borderColor="whiteAlpha.200"
									borderRadius="md"
									p={3}
								>
									<Text fontWeight="semibold" mb={2}>
										Import results
									</Text>
									<Stack gap={2}>
										{results.map((result, index) => (
											<HStack
												key={`${result.url}-${index}`}
												gap={3}
												align="flex-start"
											>
												<Icon
													as={
														result.status === "success"
															? CheckCircle2
															: AlertTriangle
													}
													color={
														result.status === "success"
															? "green.300"
															: "red.300"
													}
													mt="1"
												/>
												<Box>
													<Text fontSize="sm" fontWeight="medium">
														{result.url}
													</Text>
													{result.status === "error" && result.message ? (
														<Text fontSize="sm" color="red.300">
															{result.message}
														</Text>
													) : null}
													{result.status === "success" ? (
														<Text fontSize="sm" color="green.300">
															Imported successfully
														</Text>
													) : null}
												</Box>
											</HStack>
										))}
									</Stack>
								</Box>
							) : null}
						</Stack>
					</DialogBody>
					<DialogFooter>
						<Button
							variant="ghost"
							mr={3}
							onClick={onClose}
							isDisabled={submitting}
						>
							Cancel
						</Button>
						<Button
							colorScheme="teal"
							onClick={handleSubmit}
							isLoading={submitting}
							isDisabled={!hasUrls && !submitting}
						>
							Import
						</Button>
					</DialogFooter>
				</DialogContent>
			</DialogPositioner>
		</DialogRoot>
	);
}
