import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, originalImageUrl } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('backend boundary', () => {
  it('preserves JSON error codes and HTTP conflict status', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ error: { code: 'revision_conflict', message: 'A newer revision exists.' } }), { status: 409 })));
    await expect(api('/dossiers/id', { method: 'PATCH', body: '{}' })).rejects.toMatchObject({ code: 'revision_conflict', status: 409 });
  });
  it('does not turn HTML failures into visible backend messages', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>private debug content</html>', { status: 500 })));
    await expect(api('/health')).rejects.toMatchObject({ code: 'request_failed', message: 'The request could not be completed.' });
  });
  it('reports network failure without pretending a request completed', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('fetch failed'); }));
    await expect(api('/health')).rejects.toBeInstanceOf(ApiError);
    await expect(api('/health')).rejects.toMatchObject({ code: 'network_error', status: 0 });
  });
  it('encodes image IDs instead of constructing an arbitrary path', () => {
    expect(originalImageUrl('../private')).toBe('/api/v1/images/..%2Fprivate/content');
  });
});
