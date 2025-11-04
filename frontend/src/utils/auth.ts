// 简单的JWT Token存储与携带工具
export const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  // 默认JSON头
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    // 未授权，跳转登录
    window.location.href = '/login';
  }
  return response;
}

export async function fetchJson<T = any>(input: RequestInfo | URL, init: RequestInit = {}): Promise<T> {
  const res = await authFetch(input, init);
  if (!res.ok) {
    throw new Error(`请求失败: ${res.status}`);
  }
  return res.json();
}