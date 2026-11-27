
import { useRef, useState } from 'react'
import type {
  ChangeEvent,
  DragEvent,
} from 'react'
import {
  FileUp,
  FolderOpen,
  LoaderCircle,
} from 'lucide-react'

import { validateUploadFile } from '../../../lib/validation/uploadFile'

interface DocumentUploadProps {
  onUpload: (file: File) => void
  isUploading: boolean
  errorMessage: string | null
  isSuccess: boolean
}

/**
 * Provides file selection and drag-and-drop upload interaction.
 *
 * This component handles basic client-side validation.
 * The parent component handles the actual API mutation.
 */
export function DocumentUpload({
  onUpload,
  isUploading,
  errorMessage,
  isSuccess,
}: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const [validationError, setValidationError] =
    useState<string | null>(null)

  const [isDragging, setIsDragging] = useState(false)

  function handleFile(file: File | undefined) {
    if (!file || isUploading) {
      return
    }

    const validationMessage = validateUploadFile(file)

    if (validationMessage) {
      setValidationError(validationMessage)
      return
    }

    setValidationError(null)
    onUpload(file)
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0]

    handleFile(file)

    // Allow the user to select the same file again after an error.
    event.currentTarget.value = ''
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)

    handleFile(event.dataTransfer.files?.[0])
  }

  const displayedError = validationError ?? errorMessage

  return (
    <section
      aria-label="Document upload"
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="mb-5">
        <h3 className="text-lg font-semibold text-slate-900">
          Upload documents
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Add invoices and other supported business documents.
        </p>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={[
          'rounded-xl border-2 border-dashed p-8 text-center transition-colors',
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 bg-slate-50',
        ].join(' ')}
      >
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white text-slate-600 shadow-sm">
          {isUploading ? (
            <LoaderCircle
              aria-hidden="true"
              className="h-6 w-6 animate-spin"
            />
          ) : (
            <FileUp
              aria-hidden="true"
              className="h-6 w-6"
            />
          )}
        </div>

        <p className="mt-4 text-sm font-medium text-slate-800">
          {isUploading
            ? 'Uploading your document...'
            : 'Drag and drop your document here'}
        </p>

        <p className="mt-1 text-sm text-slate-500">
          or choose a file from your computer
        </p>

        <input
          ref={inputRef}
          id="document-upload"
          aria-label="Choose a document"
          type="file"
          accept=".pdf,.xlsx,.csv"
          disabled={isUploading}
          onChange={handleInputChange}
          className="sr-only"
        />

        <button
          type="button"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <FolderOpen
            aria-hidden="true"
            className="h-4 w-4"
          />
          Browse files
        </button>

        <p className="mt-4 text-xs text-slate-500">
          PDF, XLSX or CSV · Maximum file size: 10 MB
        </p>
      </div>

      {displayedError && (
        <div
          role="alert"
          className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {displayedError}
        </div>
      )}

      {isSuccess && !displayedError && (
        <div
          role="status"
          className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700"
        >
          Document uploaded successfully.
        </div>
      )}
    </section>
  )
}
