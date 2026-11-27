
/**
 * These limits mirror app/core/config.py on the backend.
 *
 * The backend still performs authoritative validation,
 * including checking file signatures and file contents.
 */
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

export const ALLOWED_UPLOAD_EXTENSIONS = [
  '.pdf',
  '.xlsx',
  '.csv',
] as const

/**
 * Validate basic file properties before sending a request.
 *
 * We deliberately validate the extension rather than relying
 * exclusively on browser MIME types, which can vary between systems.
 */

export function validateUploadFile(file: File): string | null {
  const lastDotIndex = file.name.lastIndexOf('.')

  const extension = lastDotIndex > 0
    ? file.name.slice(lastDotIndex).toLowerCase()
    : ''

  if (
    !ALLOWED_UPLOAD_EXTENSIONS.includes(
      extension as (typeof ALLOWED_UPLOAD_EXTENSIONS)[number],
    )
  ) {
    return 'Unsupported file type. Please select a PDF, XLSX, or CSV file.'
  }

  if (file.size === 0) {
    return 'The selected file is empty.'
  }

  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return 'The file exceeds the maximum allowed size of 10 MB.'
  }

  return null
}