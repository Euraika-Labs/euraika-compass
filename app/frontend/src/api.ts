export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init.headers);
    if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    response = await fetch(`/api/v1${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('network_error', 'The local API could not be reached.');
  }
  if (!response.ok) {
    let code = 'request_failed';
    let message = 'The request could not be completed.';
    try {
      const data: unknown = await response.json();
      if (isErrorEnvelope(data)) {
        code = data.error.code;
        message = data.error.message;
      }
    } catch { /* Non-JSON server errors are not rendered as HTML or leaked to the UI. */ }
    throw new ApiError(code, message, response.status);
  }
  return response.json() as Promise<T>;
}

function isErrorEnvelope(value: unknown): value is { error: { code: string; message: string } } {
  if (!value || typeof value !== 'object' || !('error' in value)) return false;
  const error = value.error;
  return !!error && typeof error === 'object' && 'code' in error && 'message' in error
    && typeof error.code === 'string' && typeof error.message === 'string';
}

export const originalImageUrl = (id: string) => `/api/v1/images/${encodeURIComponent(id)}/content`;
