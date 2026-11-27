
import { API_BASE_URL } from './config'

// Build API endpoint URLs consistently.
//
// Example:
// buildApiUrl('/documents/upload')
// returns:
// http://localhost:8000/api/v1/documents/upload
export function buildApiUrl(path: string): string {
  const normalizedPath = path.replace(/^\/+/, '')

  return `${API_BASE_URL}/${normalizedPath}`
}
