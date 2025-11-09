import { Box, Heading, Text } from '@chakra-ui/react';
import type { Work } from '../types/works';

interface WorkCardProps {
  work: Work;
}

export function WorkCard({ work }: WorkCardProps) {
  return (
    <Box borderRadius="lg" borderWidth="1px" borderColor="whiteAlpha.200" bg="gray.800" p={4}>
      <Heading size="md" mb={2}>
        {work.title}
      </Heading>
      <Text fontSize="sm" color="gray.400">
        #{work.id}
      </Text>
    </Box>
  );
}
