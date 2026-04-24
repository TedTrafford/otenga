import { create } from 'zustand'
import { authApi, default as client } from '../api/client'
import toast from 'react-hot-toast'

const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('otenga_user') || 'null'),
  token: localStorage.getItem('otenga_token') || null,
  isLoading: false,
  isAuthenticated: !!localStorage.getItem('otenga_token'),

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      const { data } = await authApi.login({ username, password })
      localStorage.setItem('otenga_token', data.access_token)
      localStorage.setItem('otenga_user', JSON.stringify(data.user))
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isLoading: false })
      toast.success(`Welcome back, ${data.user.username}!`)
      return true
    } catch (err) {
      set({ isLoading: false })
      toast.error(err.response?.data?.detail || 'Login failed')
      return false
    }
  },

  loginWithSSOToken: async (laravelToken) => {
    set({ isLoading: true })
    try {
      const { data } = await client.post('/auth/sso', { token: laravelToken })
      localStorage.setItem('otenga_token', data.access_token)
      localStorage.setItem('otenga_user', JSON.stringify(data.user))
      set({ user: data.user, token: data.access_token, isAuthenticated: true, isLoading: false })
      toast.success(`Welcome, ${data.user.full_name || data.user.username}!`)
      return true
    } catch (err) {
      set({ isLoading: false })
      toast.error(err.response?.data?.detail || 'SSO login failed')
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('otenga_token')
    localStorage.removeItem('otenga_user')
    set({ user: null, token: null, isAuthenticated: false })
    toast.success('Logged out successfully')
  },

  refreshUser: async () => {
    try {
      const { data } = await authApi.me()
      localStorage.setItem('otenga_user', JSON.stringify(data))
      set({ user: data })
    } catch {
      get().logout()
    }
  },

  isCreator: () => {
    const { user } = get()
    return user?.role === 'creator' || user?.role === 'superuser'
  },

  isSuperuser: () => {
    const { user } = get()
    return user?.role === 'superuser'
  },
}))

export default useAuthStore
