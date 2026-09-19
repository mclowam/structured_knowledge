export interface KnowledgeCreate {
  title: string
  description?: string
}

export interface KnowledgeUpdate {
  title?: string
  description?: string
}

export interface KnowledgeResponse {
  id: string
  user_id: string
  title: string
  description?: string
  created_at: string
  updated_at?: string
}
