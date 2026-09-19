import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteKnowledge, getKnowledge, updateKnowledge } from '../api/knowledge'
import {
  createLibraryFromFile,
  createLibraryFromUrl,
  deleteLibrary,
  listLibraries,
} from '../api/library'
import { ApiError } from '../api/client'
import type { KnowledgeResponse } from '../types/knowledge'
import type { LibraryResponse } from '../types/library'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.detail : 'request failed'
}

const IN_PROGRESS = new Set(['pending', 'extracting', 'extracted', 'compressing'])

export function KnowledgeDetailPage() {
  const { knowledgeId } = useParams()
  const navigate = useNavigate()
  const [knowledge, setKnowledge] = useState<KnowledgeResponse | null>(null)
  const [libraries, setLibraries] = useState<LibraryResponse[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [url, setUrl] = useState('')
  const [urlTitle, setUrlTitle] = useState('')
  const [fileTitle, setFileTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    if (!knowledgeId) return
    const [kb, libs] = await Promise.all([getKnowledge(knowledgeId), listLibraries(knowledgeId)])
    setKnowledge(kb)
    setTitle(kb.title)
    setDescription(kb.description ?? '')
    setLibraries(libs)
  }

  useEffect(() => {
    load().catch((err: unknown) => setError(errorMessage(err)))
  }, [knowledgeId])

  const shouldPoll = libraries.some((item) => IN_PROGRESS.has(item.status))

  useEffect(() => {
    if (!knowledgeId || !shouldPoll) return
    const timer = window.setInterval(() => {
      listLibraries(knowledgeId)
        .then(setLibraries)
        .catch((err: unknown) => setError(errorMessage(err)))
    }, 3000)
    return () => window.clearInterval(timer)
  }, [knowledgeId, shouldPoll])

  if (!knowledgeId) return <p>missing id</p>
  if (!knowledge && !error) return <p className="layout">loading...</p>

  return (
    <div className="layout">
      <p>
        <Link to="/">← all knowledge</Link>
      </p>
      <h1>{knowledge?.title ?? 'Knowledge'}</h1>
      {error ? <div className="error">{error}</div> : null}

      <form
        className="card"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setError('')
          try {
            const updated = await updateKnowledge(knowledgeId, {
              title,
              description: description.trim() || undefined,
            })
            setKnowledge(updated)
          } catch (err) {
            setError(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <h3>Edit</h3>
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        <div className="row">
          <button type="submit" disabled={busy}>
            save
          </button>
          <button
            type="button"
            onClick={async () => {
              if (!confirm('delete this knowledge base?')) return
              try {
                await deleteKnowledge(knowledgeId)
                navigate('/')
              } catch (err) {
                setError(errorMessage(err))
              }
            }}
          >
            delete
          </button>
        </div>
      </form>

      <form
        className="card"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setError('')
          try {
            await createLibraryFromUrl(knowledgeId, {
              url,
              title: urlTitle.trim() || undefined,
            })
            setUrl('')
            setUrlTitle('')
            await load()
          } catch (err) {
            setError(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <h3>Add URL</h3>
        <input
          placeholder="https://..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <input
          placeholder="title (optional)"
          value={urlTitle}
          onChange={(e) => setUrlTitle(e.target.value)}
        />
        <button type="submit" disabled={busy}>
          add url
        </button>
      </form>

      <form
        className="card"
        onSubmit={async (event) => {
          event.preventDefault()
          if (!file) return
          setBusy(true)
          setError('')
          try {
            await createLibraryFromFile(knowledgeId, file, fileTitle)
            setFile(null)
            setFileTitle('')
            event.currentTarget.reset()
            await load()
          } catch (err) {
            setError(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <h3>Upload file</h3>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
        <input
          placeholder="title (optional)"
          value={fileTitle}
          onChange={(e) => setFileTitle(e.target.value)}
        />
        <button type="submit" disabled={busy || !file}>
          upload
        </button>
      </form>

      <div className="card">
        <h3>Libraries</h3>
        {libraries.length === 0 ? (
          <p className="muted">no items yet</p>
        ) : (
          <ul>
            {libraries.map((item) => (
              <li key={item.id} className="list-item">
                <Link to={`/libraries/${item.id}`}>{item.title || item.original_ref}</Link>
                <span className="muted">
                  {' '}
                  [{item.source_type}] {item.status}
                </span>
                <button
                  type="button"
                  onClick={async () => {
                    if (!confirm('delete this library item?')) return
                    try {
                      await deleteLibrary(item.id)
                      await load()
                    } catch (err) {
                      setError(errorMessage(err))
                    }
                  }}
                >
                  delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
