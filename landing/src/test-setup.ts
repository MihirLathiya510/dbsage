import '@testing-library/jest-dom';
import { vi } from 'vitest';

// jsdom does not implement navigator.clipboard — mock it globally
Object.defineProperty(navigator, 'clipboard', {
	value: { writeText: vi.fn().mockResolvedValue(undefined) },
	writable: true,
});
