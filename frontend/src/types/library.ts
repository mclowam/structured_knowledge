export interface LibraryResponse {
  id: string
  knowledge_id: string
  source_type: string
  original_ref: string
  title?: string
  status: string
  error_message?: string
  text_content?: string
  compressed_content?: string
  order?: number
  created_at: string
  updated_at?: string
}

export interface LibraryUrlCreate {
  url: string
  title?: string
}
