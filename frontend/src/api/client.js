import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('otenga_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('otenga_token')
      localStorage.removeItem('otenga_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login:    (data) => client.post('/auth/login', data),
  register: (data) => client.post('/auth/register', data),
  me:       ()     => client.get('/auth/me'),
}

export const notebooksApi = {
  list:     ()           => client.get('/notebooks/'),
  get:      (id)         => client.get(`/notebooks/${id}`),
  create:   (data)       => client.post('/notebooks/', data),
  update:   (id, data)   => client.put(`/notebooks/${id}`, data),
  delete:   (id)         => client.delete(`/notebooks/${id}`),
  publish:  (id)         => client.post(`/notebooks/${id}/publish`),
  approve:  (id)         => client.post(`/notebooks/${id}/approve`),
}

export const executionApi = {
  executeCell: (data)  => client.post('/execute/cell', data),
  getTables:   ()      => client.get('/execute/schema/tables'),
  getSchema:   (table) => client.get(`/execute/schema/tables/${table}`),
  clearCtx:    (id)    => client.delete(`/execute/context/${id}`),
}

export const dashboardsApi = {
  list:        ()         => client.get('/dashboards/'),
  pending:     ()         => client.get('/dashboards/pending'),
  get:         (id)       => client.get(`/dashboards/${id}`),
  create:      (data)     => client.post('/dashboards/', data),
  update:      (id, data) => client.put(`/dashboards/${id}`, data),
  delete:      (id)       => client.delete(`/dashboards/${id}`),
  submit:      (id)       => client.post(`/dashboards/${id}/submit`),
  publish:     (id)       => client.post(`/dashboards/${id}/publish`),
  unpublish:   (id)       => client.post(`/dashboards/${id}/unpublish`),
}

export const usersApi = {
  list:          ()         => client.get('/users/'),
  pending:       ()         => client.get('/users/pending'),
  unverified:    ()         => client.get('/users/unverified'),
  get:           (id)       => client.get(`/users/${id}`),
  update:        (id, data) => client.put(`/users/${id}`, data),
  approve:       (id)       => client.post(`/users/${id}/approve`),
  adminVerify:   (id)       => client.post(`/users/${id}/verify-email`),
  disable:       (id)       => client.post(`/users/${id}/disable`),
  enable:        (id)       => client.post(`/users/${id}/enable`),
  delete:        (id)       => client.delete(`/users/${id}`),
  auditLogs:     ()         => client.get('/users/audit/logs'),
}

export default client
