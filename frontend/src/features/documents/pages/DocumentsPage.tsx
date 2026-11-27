export function DocumentsPage() {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Document workspace
        </h2>

        <p className="mt-2 text-sm text-slate-600">
          Upload business documents, inspect extracted information,
          and review extraction results.
        </p>
      </div>

      {/* Upload functionality will be implemented in a later chunk. */}
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h3 className="text-base font-medium">
          Your document workspace
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Document upload and processing will be available here.
        </p>
      </div>
    </section>
  )
}
