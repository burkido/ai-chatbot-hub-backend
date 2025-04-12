export type Body_login_login_access_token = {
  grant_type?: string | null
  username: string
  password: string
  scope?: string
  client_id?: string | null
  client_secret?: string | null
}

export type HTTPValidationError = {
  detail?: Array<ValidationError>
}

export type DocumentCreate = {
  index_name: string
  namespace?: string | null
  file: File
}

export type Message = {
  message: string
}

export type UploadDocumentResponse = {
  message: string
  document_id: string
  chunk_count: number
}

export type DeleteDocumentResponse = {
  message: string
  deleted_ids: string[]
}

export type NewPassword = {
  token: string
  new_password: string
}

export type Token = {
  access_token: string
  refresh_token: string
  token_type?: string
  user_id: string
  application_id: string
  is_premium: boolean
  remaining_credit: number
}

export type RefreshTokenRequest = {
  refresh_token: string
}

export type UpdatePassword = {
  current_password: string
  new_password: string
}

export type UserCreate = {
  email: string
  is_active?: boolean
  is_superuser?: boolean
  full_name?: string | null
  password: string
}

export type UserPublic = {
  email: string
  is_active?: boolean
  is_superuser?: boolean
  full_name?: string | null
  id: string
  credit: number
  is_premium: boolean
  is_verified: boolean
}

export type UserRegister = {
  email: string
  password: string
  full_name?: string | null
}

export type UserUpdate = {
  email?: string | null
  is_active?: boolean
  is_superuser?: boolean
  full_name?: string | null
  password?: string | null
  credit?: number
  is_premium?: boolean
  is_verified?: boolean
}

export type UserUpdateMe = {
  full_name?: string | null
  email?: string | null
}

export type UsersPublic = {
  data: Array<UserPublic>
  count: number
}

export type ValidationError = {
  loc: Array<string | number>
  msg: string
  type: string
}

export type UserStatPoint = {
  date: string
  count: number
}

export type ApplicationUserStats = {
  application_id: string
  application_name: string
  data_points: UserStatPoint[]
  current_count: number
}

export type UserStatistics = {
  total_users: number
  by_application: ApplicationUserStats[]
}
