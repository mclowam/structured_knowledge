import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext'
import { ProtectedRoute } from '../auth/ProtectedRoute'
import { KnowledgeDetailPage } from '../pages/KnowledgeDetailPage'
import { KnowledgeListPage } from '../pages/KnowledgeListPage'
import { LibraryDetailPage } from '../pages/LibraryDetailPage'
import { LoginPage } from '../pages/LoginPage'
import { RegisterPage } from '../pages/RegisterPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <KnowledgeListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/knowledge/:knowledgeId"
            element={
              <ProtectedRoute>
                <KnowledgeDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/libraries/:libraryId"
            element={
              <ProtectedRoute>
                <LibraryDetailPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
