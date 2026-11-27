import type { ZodType } from 'zod'
import { buildApiUrl } from './urls'
import { ApiError, getApiErrorMessage } from './apiErrors'

/**
 * Shared options for API requests.
 *
 * An AbortSignal allows a component or query to cancel
 * an ongoing request when it is no longer needed.
 */
interface ApiRequestOptions {
  signal?: AbortSignal
  headers?: HeadersInit
}

/**
 * Read an error response safely.
 *
 * FastAPI normally responds with JSON, but a proxy or server
 * may return plain text or an empty response.
 */
async function readErrorDetails(
  response: Response,
): Promise<unknown> {
  const responseText = await response.text()

  if (!responseText) {
    return null
  }

  try {
    return JSON.parse(responseText) as unknown
  } catch {
    return responseText
  }
}

/**
 * Convert unsuccessful HTTP responses into ApiError.
 */
async function handleResponseError(
  response: Response,
): Promise<never> {
  const details = await readErrorDetails(response)

  const message = getApiErrorMessage(
    details,
    `API request failed with status ${response.status}`,
  )

  throw new ApiError(
    message,
    response.status,
    details,
  )
}

/**
 * Shared request function for JSON API responses.
 *
 * Endpoint-specific Zod schemas will validate the returned
 * JSON before it is used by the application.
 */
async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)

  // All JSON API requests advertise that they accept JSON.
  headers.set('Accept', 'application/json')

  try {
    const response = await fetch(buildApiUrl(path), {
      ...options,
      headers,
    })

    if (!response.ok) {
      await handleResponseError(response)
    }

    if (response.status === 204) {
      return undefined as T
    }

    try {
      return await response.json() as T
    } catch {
      throw new ApiError(
        'The server returned an invalid JSON response.',
        response.status,
      )
    }
  } catch (error) {
    // Preserve meaningful API errors and request cancellation.
    if (
      error instanceof ApiError ||
      (error instanceof DOMException && error.name === 'AbortError')
    ) {
      throw error
    }

    throw new ApiError(
      'Unable to connect to the server. Check your connection and try again.',
      null,
      error,
    )
  }
}

/**
 * GET JSON resource.
 */
export function apiGet<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  return requestJson<T>(path, {
    method: 'GET',
    signal: options.signal,
    headers: options.headers,
  })
}

/**
 * Sends a POST request without a request body.
 *
 * Use this for backend endpoints that do not accept JSON input.
 * For example, the document processing endpoint.
 */
export function apiPostEmpty<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: 'POST',
    signal: options.signal,
    headers: options.headers,
  })
}



/**
 * POST a JSON request body.
 */
export function apiPost<TResponse, TBody>(
  path: string,
  body: TBody,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const headers = new Headers(options.headers)

  headers.set('Content-Type', 'application/json')

  return requestJson<TResponse>(path, {
    method: 'POST',
    signal: options.signal,
    headers,
    body: JSON.stringify(body),
  })
}

/**
 * POST a file using multipart/form-data.
 *
 * Important:
 * Do not set Content-Type manually here.
 * The browser must generate the multipart boundary.
 */
export function apiPostFile<TResponse>(
  path: string,
  file: File,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const formData = new FormData()

  // This matches the backend UploadFile parameter name.
  formData.append('file', file)

  const headers = new Headers(options.headers)

  headers.set('Accept', 'application/json')

  // No Content-Type header: fetch generates the boundary.
  return requestJson<TResponse>(path, {
    method: 'POST',
    signal: options.signal,
    headers,
    body: formData,
  })
}

/**
 * GET a file as a Blob.
 *
 * Used for downloading the original uploaded document.
 */
export async function apiGetBlob(
  path: string,
  options: ApiRequestOptions = {},
): Promise<Blob> {
  const headers = new Headers(options.headers)

  try {
    const response = await fetch(buildApiUrl(path), {
      method: 'GET',
      signal: options.signal,
      headers,
    })

    if (!response.ok) {
      await handleResponseError(response)
    }

    return await response.blob()
  } catch (error) {
    if (
      error instanceof ApiError ||
      (error instanceof DOMException && error.name === 'AbortError')
    ) {
      throw error
    }

    throw new ApiError(
      'Unable to download the document. Check your connection and try again.',
      null,
      error,
    )
  }
}

/**
 * Validate an API response against its Zod schema.
 *
 * This prevents unexpected backend data from silently
 * entering the frontend application.
 */
export function validateApiResponse<T>(
  schema: ZodType<T>,
  data: unknown,
): T {
  const result = schema.safeParse(data)

  if (!result.success) {
    throw new ApiError(
      'The server returned data that does not match the expected API contract.',
      null,
      result.error.issues,
    )
  }

  return result.data
}