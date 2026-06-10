import { defineStore } from 'pinia'
import { authApi } from '../api'
import router from '../router'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('shopminer_token') || '',
    currentUser: JSON.parse(localStorage.getItem('shopminer_user') || 'null'),
    cartCount: 0,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.currentUser?.role === 'admin',
    displayName: (state) => {
      if (!state.currentUser) return ''
      return `${state.currentUser.first_name} ${state.currentUser.last_name}`
    },
  },

  actions: {
    async login(email, password) {
      const res = await authApi.login(email, password)
      this.token = res.data.access_token
      this.currentUser = res.data.user
      localStorage.setItem('shopminer_token', this.token)
      localStorage.setItem('shopminer_user', JSON.stringify(this.currentUser))
    },

    async register(data) {
      const res = await authApi.register(data)
      this.token = res.data.access_token
      this.currentUser = res.data.user
      localStorage.setItem('shopminer_token', this.token)
      localStorage.setItem('shopminer_user', JSON.stringify(this.currentUser))
    },

    async fetchMe() {
      try {
        const res = await authApi.getMe()
        this.currentUser = res.data
        localStorage.setItem('shopminer_user', JSON.stringify(this.currentUser))
      } catch {
        this.logout()
      }
    },

    logout() {
      this.token = ''
      this.currentUser = null
      this.cartCount = 0
      localStorage.removeItem('shopminer_token')
      localStorage.removeItem('shopminer_user')
      router.push({ name: 'Home' })
    },

    async fetchCartCount() {
      if (!this.isLoggedIn) {
        this.cartCount = 0
        return
      }
      try {
        const { cartApi } = await import('../api')
        const res = await cartApi.getCart()
        this.cartCount = res.data.item_count || 0
      } catch {
        this.cartCount = 0
      }
    },
  },
})
