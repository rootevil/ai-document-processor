/**
 * Normalized API error.
 *
 * Keeps HTTP status and backend error details together so
 * the UI can display useful messages consistently.
 */
export class ApiError extends Error {
  readonly status: number | null
  readonly details: unknown

  constructor(
    message: string,
    status: number | null = null,
    details: unknown = null,
  ) {
    super(message)

    this.name = 'ApiError'
    this.status = status
    this.details = details

    Object.setPrototypeOf(this, ApiError.prototype)
  }
}

/**
 * Extract a readable message from FastAPI error responses.
 *
 * FastAPI commonly returns:
 * { "detail": "Document not found" }
 *
 * Validation errors may return:
 * { "detail": [{ "msg": "...", "loc": [...] }] }
 */
export function getApiErrorMessage(
  details: unknown,
  fallback: string,
): string {
  if (typeof details === 'string') {
    return details
  }

  if (
    typeof details === 'object' &&
    details !== null &&
    'detail' in details
  ) {
    const detail = details.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (
            typeof item === 'object' &&
            item !== null &&
            'msg' in item &&
            typeof item.msg === 'string'
          ) {
            return item.msg
          }

          return null
        })
        .filter((message): message is string => message !== null)

      if (messages.length > 0) {
        return messages.join('; ')
      }
    }
  }

  return fallback
}