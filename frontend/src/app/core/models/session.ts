export type Role = 'admin' | 'lector';

export interface Session {
  username: string;
  role: Role;
  csrf_token: string;
  expires_at: string;
  idle_expires_at?: string;
}
