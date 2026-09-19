export interface RegisterRequest {
  username: string
  password: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RegisterResponse {
  user_id: string
  username: string
}

export interface UserPayload {
  user_id: string
  username: string
  is_staff: boolean
}

export interface RefreshRequest {
  refresh_token: string
}
