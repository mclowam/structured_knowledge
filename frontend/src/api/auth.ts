import { apiJson, clearTokens, setTokens } from './client'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserPayload,
} from '../types/auth'

export async function register(payload: RegisterRequest): Promise<RegisterResponse> {
  return apiJson<RegisterResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const tokens = await apiJson<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  setTokens(tokens.access_token, tokens.refresh_token)
  return tokens
}

export async function me(): Promise<UserPayload> {
  return apiJson<UserPayload>('/auth/me')
}

export function logout(): void {
  clearTokens()
}
