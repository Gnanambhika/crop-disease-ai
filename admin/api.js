export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export class Api {
  constructor() { this.token = null; }
  async request(path, method = 'GET', body) {
    const headers = { Accept: 'application/json' };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let response;
    try {
      response = await fetch(`/api${path}`, {
        method, headers, body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(15000), cache: 'no-store',
      });
    } catch { throw new ApiError('Cannot reach the server. Please try again.', 0); }
    if (!response.ok) {
      let detail;
      try { detail = (await response.json()).detail; } catch { /* non-JSON failure */ }
      const message = response.status === 401 ? 'Your session expired or the credentials are incorrect. Sign in again.'
        : response.status === 403 ? 'Administrator access is required.'
        : response.status === 422 ? 'Check the required fields and text lengths.'
        : response.status < 500 && typeof detail === 'string' ? detail
        : 'The server could not complete this action. Please try again.';
      throw new ApiError(message, response.status);
    }
    if (response.status === 204) return null;
    try { return await response.json(); }
    catch { throw new ApiError('The server returned an unreadable response. Please refresh and try again.', response.status); }
  }
  async login(email, password) {
    this.token = null;
    const result = await this.request('/auth/login', 'POST', {email, password});
    this.token = result.access_token;
    try {
      const user = await this.request('/auth/me');
      if (user.role !== 'admin') throw new ApiError('Administrator access is required.', 403);
      return user;
    } catch (error) { this.token = null; throw error; }
  }
}
