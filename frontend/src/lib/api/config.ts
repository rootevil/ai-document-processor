import { z } from 'zod'

// Validate frontend environment variables at application startup.
const environmentSchema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .url('VITE_API_BASE_URL must be a valid URL')
    .transform((value) => value.replace(/\/+$/, '')),
})

// Read and validate Vite environment variables.
const environmentResult = environmentSchema.safeParse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
})

// Fail early with a useful error instead of making requests
// to an undefined or incorrectly configured backend URL.
if (!environmentResult.success) {
  console.error(
    'Frontend environment configuration is invalid:',
    z.treeifyError(environmentResult.error),
  )

  throw new Error(
    'Invalid frontend API configuration. Check frontend/.env.local.',
  )
}

// Export one centralized backend URL for the application.
export const API_BASE_URL =
  environmentResult.data.VITE_API_BASE_URL
