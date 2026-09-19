import { apiJson } from './client'
import type { KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate } from '../types/knowledge'

export function listKnowledge(): Promise<KnowledgeResponse[]> {
  return apiJson<KnowledgeResponse[]>('/api/v1/knowledge')
}

export function getKnowledge(id: string): Promise<KnowledgeResponse> {
  return apiJson<KnowledgeResponse>(`/api/v1/knowledge/${id}`)
}

export function createKnowledge(payload: KnowledgeCreate): Promise<KnowledgeResponse> {
  return apiJson<KnowledgeResponse>('/api/v1/knowledge', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateKnowledge(id: string, payload: KnowledgeUpdate): Promise<KnowledgeResponse> {
  return apiJson<KnowledgeResponse>(`/api/v1/knowledge/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteKnowledge(id: string): Promise<void> {
  return apiJson<void>(`/api/v1/knowledge/${id}`, { method: 'DELETE' })
}
