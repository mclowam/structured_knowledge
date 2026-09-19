import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteLibrary, getLibrary } from '../api/library'
import { ApiError } from '../api/client'
import type { LibraryResponse } from '../types/library'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.detail : 'request failed'
}

const IN_PROGRESS = new Set(['pending', 'extracting', 'extracted', 'compressing'])

export function LibraryDetailPage() {
  const { libraryId } = useParams()
  const navigate = useNavigate()
  const [item, setItem] = useState<LibraryResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!libraryId) return
    getLibrary(libraryId)
      .then(setItem)
      .catch((err: unknown) => setError(errorMessage(err)))
  }, [libraryId])

  useEffect(() => {
    if (!libraryId || !item || !IN_PROGRESS.has(item.status)) return
    const timer = window.setInterval(() => {
      getLibrary(libraryId)
        .then(setItem)
        .catch((err: unknown) => setError(errorMessage(err)))
    }, 3000)
    return () => window.clearInterval(timer)
  }, [libraryId, item])

  if (!item && !error) return <p className="layout">loading...</p>

  return (
    <div className="layout">
      {item ? (
        <p>
          <Link to={`/knowledge/${item.knowledge_id}`}>← knowledge</Link>
        </p>
      ) : null}
      <h1>{item?.title || 'Library item'}</h1>
      {error ? <div className="error">{error}</div> : null}
      {item ? (
        <>
          <div className="card">
            <p>status: {item.status}</p>
            <p>source: {item.source_type}</p>
            <p>ref: {item.original_ref}</p>
            {item.error_message ? <p className="error">{item.error_message}</p> : null}
            <button
              type="button"
              onClick={async () => {
                if (!confirm('delete this library item?')) return
                try {
                  await deleteLibrary(item.id)
                  navigate(`/knowledge/${item.knowledge_id}`)
                } catch (err) {
                  setError(errorMessage(err))
                }
              }}
            >
              delete
            </button>
          </div>
          <div className="card">
            <h3>Extracted text</h3>
            <pre>{item.text_content || '—'}</pre>
          </div>
          <div className="card">
            <h3>Compressed</h3>
            <pre>{item.compressed_content || '—'}</pre>
          </div>
        </>
      ) : null}
    </div>
  )
}
