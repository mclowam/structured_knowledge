import { apiJson } from './client'
import type { LibraryResponse, LibraryUrlCreate } from '../types/library'

export function listLibraries(knowledgeId: string): Promise<LibraryResponse[]> {
  return apiJson<LibraryResponse[]>(`/api/v1/knowledge/${knowledgeId}/libraries`)
}

export function getLibrary(id: string): Promise<LibraryResponse> {
  return apiJson<LibraryResponse>(`/api/v1/libraries/${id}`)
}

export function createLibraryFromUrl(
  knowledgeId: string,
  payload: LibraryUrlCreate,
): Promise<LibraryResponse> {
  return apiJson<LibraryResponse>(`/api/v1/knowledge/${knowledgeId}/libraries`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createLibraryFromFile(
  knowledgeId: string,
  file: File,
  title?: string,
): Promise<LibraryResponse> {
  const form = new FormData()
  form.append('file', file)
  if (title?.trim()) form.append('title', title.trim())
  return apiJson<LibraryResponse>(`/api/v1/knowledge/${knowledgeId}/libraries`, {
    method: 'POST',
    body: form,
  })
}

export function deleteLibrary(id: string): Promise<void> {
  return apiJson<void>(`/api/v1/libraries/${id}`, { method: 'DELETE' })
}
