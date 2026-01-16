import {
    Button,
    HStack,
    Input,
    Pagination as ChakraPagination,
    Popover,
    Portal,
    Stack,
    Text,
} from "@chakra-ui/react";
import { useState } from "react";

interface PaginationProps {
    currentPage: number; // 0-indexed
    totalPages: number;
    onPageChange: (page: number) => void;
    showGoTo?: boolean;
}

export function Pagination({
    currentPage,
    totalPages,
    onPageChange,
    showGoTo = true,
}: PaginationProps) {
    const [gotoPage, setGotoPage] = useState("");
    const [isPopoverOpen, setIsPopoverOpen] = useState(false);

    const handleGoTo = () => {
        const page = Number.parseInt(gotoPage, 10);
        if (!Number.isNaN(page) && page >= 1 && page <= totalPages) {
            onPageChange(page - 1); // Convert 1-based input to 0-based index
            setGotoPage("");
            setIsPopoverOpen(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            handleGoTo();
        }
    };

    // Chakra V3 Pagination usually works with count/pageSize or count directly if plain.
    // We only have totalPages. So let's fake count=totalPages, pageSize=1.
    const count = totalPages;
    const pageSize = 1;

    return (
        <ChakraPagination.Root
            count={count}
            pageSize={pageSize}
            page={currentPage + 1}
            onPageChange={(e) => onPageChange(e.page - 1)}
        >
            <HStack wrap="wrap" gap={2}>
                <ChakraPagination.PrevTrigger asChild>
                    <Button variant="outline" size="sm">
                        Previous
                    </Button>
                </ChakraPagination.PrevTrigger>

                <ChakraPagination.Items
                    render={(page) => (
                        <Button
                            variant={page.type === "page" ? "outline" : "ghost"}
                            size="sm"
                        >
                            {page.type === "page" ? page.value : "..."}
                        </Button>
                    )}
                />

                {showGoTo && (
                    <Popover.Root open={isPopoverOpen} onOpenChange={(e) => setIsPopoverOpen(e.open)}>
                        <Popover.Trigger asChild>
                            <Button variant="ghost" size="sm" fontWeight="normal" color="gray.500">
                                Jump to...
                            </Button>
                        </Popover.Trigger>
                        <Portal>
                            <Popover.Positioner>
                                <Popover.Content width="200px">
                                    <Popover.Body>
                                        <Stack gap={3}>
                                            <Text fontSize="sm" fontWeight="medium">
                                                Go to page:
                                            </Text>
                                            <Input
                                                size="sm"
                                                type="number"
                                                min={1}
                                                max={totalPages}
                                                placeholder={`1-${totalPages}`}
                                                value={gotoPage}
                                                onChange={(e) => setGotoPage(e.target.value)}
                                                onKeyDown={handleKeyDown}
                                                autoFocus
                                            />
                                            <Button size="sm" colorScheme="teal" onClick={handleGoTo}>
                                                Go
                                            </Button>
                                        </Stack>
                                    </Popover.Body>
                                </Popover.Content>
                            </Popover.Positioner>
                        </Portal>
                    </Popover.Root>
                )}

                <ChakraPagination.NextTrigger asChild>
                    <Button variant="outline" size="sm">
                        Next
                    </Button>
                </ChakraPagination.NextTrigger>
            </HStack>
        </ChakraPagination.Root>
    );
}
