import { defineStore } from 'pinia'
import { cartApi } from '../api'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [],
    loading: false,
  }),

  getters: {
    totalAmount: (state) => state.items.reduce((sum, i) => sum + i.price * i.quantity, 0),
    itemCount: (state) => state.items.length,
  },

  actions: {
    async fetchCart() {
      this.loading = true
      try {
        const res = await cartApi.getCart()
        this.items = res.data.items || []
      } finally {
        this.loading = false
      }
    },

    async addItem(productId, quantity = 1) {
      const res = await cartApi.addToCart(productId, quantity)
      this.items = res.data || []
      await this._syncCartCount()
    },

    async updateItem(productId, quantity) {
      const res = await cartApi.updateItem(productId, quantity)
      this.items = res.data || []
    },

    async removeItem(productId) {
      const res = await cartApi.removeItem(productId)
      this.items = res.data || []
      await this._syncCartCount()
    },

    async clearCart() {
      await cartApi.clearCart()
      this.items = []
      await this._syncCartCount()
    },

    async _syncCartCount() {
      const { useUserStore } = await import('./user')
      const userStore = useUserStore()
      userStore.cartCount = this.items.length
    },
  },
})
