import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createKnowledge, deleteKnowledge, listKnowledge } from '../api/knowledge'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { KnowledgeResponse } from '../types/knowledge'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.detail : 'request failed'
}

export function KnowledgeListPage() {
  const { user, logout } = useAuth()
  const [items, setItems] = useState<KnowledgeResponse[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    try {
      setItems(await listKnowledge())
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div className="layout">
      <div className="header">
        <h1>Knowledge</h1>
        <div className="row">
          <span className="muted">{user?.username}</span>
          <button type="button" onClick={logout}>
            logout
          </button>
        </div>
      </div>

      <form
        className="card"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setError('')
          try {
            await createKnowledge({
              title,
              description: description.trim() || undefined,
            })
            setTitle('')
            setDescription('')
            await load()
          } catch (err) {
            setError(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <h3>Create</h3>
        <input
          placeholder="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
        <button type="submit" disabled={busy}>
          create
        </button>
      </form>

      {error ? <div className="error">{error}</div> : null}

      <div className="card">
        {items.length === 0 ? (
          <p className="muted">no knowledge bases yet</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={item.id} className="list-item">
                <Link to={`/knowledge/${item.id}`}>{item.title}</Link>
                {item.description ? <span className="muted"> — {item.description}</span> : null}
                <button
                  type="button"
                  onClick={async () => {
                    if (!confirm(`delete "${item.title}"?`)) return
                    try {
                      await deleteKnowledge(item.id)
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
