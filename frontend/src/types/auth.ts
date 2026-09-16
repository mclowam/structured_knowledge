export interface RegisterRequest {
    username: string;
    password: string;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string
    refresh_token: string
}

export interface UserPayload {
    user_id: string
    username: string
    is_staff: boolean
}

export interface UpdateUserRequest {
    username?: string
    password?: string
}