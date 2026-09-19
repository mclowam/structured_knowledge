import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.detail : 'request failed'
}

export function RegisterPage() {
  const { user, register } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  return (
    <div className="layout">
      <h1>Register</h1>
      <form
        className="card"
        onSubmit={async (event) => {
          event.preventDefault()
          setBusy(true)
          setError('')
          try {
            await register(username, password)
          } catch (err) {
            setError(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <input
          placeholder="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error ? <div className="error">{error}</div> : null}
        <button type="submit" disabled={busy}>
          register
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">login</Link>
      </p>
    </div>
  )
}
