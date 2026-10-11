import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

const worker = setupWorker(...handlers);

export async function startMockWorker(): Promise<void> {
  const enableMocks = import.meta.env.VITE_ENABLE_MOCKS === 'true';
  if (!enableMocks) {
    return;
  }
  await worker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: {
      url: '/mockServiceWorker.js',
    },
  });
}

export { worker };
