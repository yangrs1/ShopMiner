import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截器：自动注入 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('shopminer_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
http.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code && data.code !== 200 && data.code !== 201) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        const requestUrl = error.config?.url || ''
        if (requestUrl.includes('/auth/login')) {
          ElMessage.error('邮箱或密码错误，请重试')
        } else {
          localStorage.removeItem('shopminer_token')
          localStorage.removeItem('shopminer_user')
          ElMessage.warning('登录已过期，请重新登录')
          router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      } else if (status === 403) {
        ElMessage.error('无权限访问')
      } else if (status === 404) {
        ElMessage.error('资源不存在')
      } else {
        ElMessage.error(data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查连接')
    }
    return Promise.reject(error)
  }
)

// ============================================================
// Auth API
// ============================================================
export const authApi = {
  login: (email, password) => http.post('/auth/login', { email, password }),
  register: (data) => http.post('/auth/register', data),
  getMe: () => http.get('/auth/me'),
  updateMe: (data) => http.put('/auth/me', data),
  recharge: (amount) => http.post('/auth/me/recharge', { amount }),
}

// ============================================================
// Product API
// ============================================================
export const productApi = {
  getProducts: (params) => http.get('/products', { params }),
  getCategories: () => http.get('/products/categories'),
  getProduct: (id) => http.get(`/products/${id}`),
  getProductRating: (id) => http.get(`/products/${id}/rating`),
  getProductsRatings: (productIds) => http.get('/products/ratings', { params: { product_ids: productIds.join(',') } }),
}

// ============================================================
// Cart API
// ============================================================
export const cartApi = {
  getCart: () => http.get('/cart'),
  addToCart: (product_id, quantity = 1) => http.post('/cart', { product_id, quantity }),
  updateItem: (product_id, quantity) => http.put(`/cart/${product_id}`, { quantity }),
  removeItem: (product_id) => http.delete(`/cart/${product_id}`),
  clearCart: () => http.delete('/cart'),
}

// ============================================================
// Order API
// ============================================================
export const orderApi = {
  createOrder: (data = {}) => http.post('/orders', data),
  getOrders: (params) => http.get('/orders', { params }),
  getOrder: (id) => http.get(`/orders/${id}`),
  cancelOrder: (id) => http.post(`/orders/${id}/cancel`),
  payOrder: (id) => http.post(`/orders/${id}/pay`, {}),
  confirmDelivery: (id) => http.post(`/orders/${id}/deliver`, {}),
  getStatusLogs: (id) => http.get(`/orders/${id}/status-logs`),
}

// ============================================================
// Favorites API
// ============================================================
export const favoriteApi = {
  list: (params) => http.get('/favorites', { params }),
  add: (productId) => http.post('/favorites', { product_id: productId }),
  remove: (productId) => http.delete(`/favorites/${productId}`),
  check: (productId) => http.get(`/favorites/check/${productId}`),
}

// ============================================================
// Analytics API (User)
// ============================================================
export const analyticsApi = {
  getUserRfm: () => http.get('/analytics/user/rfm'),
  getUserTrend: () => http.get('/analytics/user/trend'),
  getUserCategoryPreference: () => http.get('/analytics/user/category-preference'),
  getAssociationForProduct: (productId) => http.get(`/analytics/association/product/${productId}`),
  getHotProducts: (params) => http.get('/analytics/products/hot', { params }),
  getReviews: (productId, params) => http.get(`/reviews/product/${productId}`, { params }),
  createReview: (data) => http.post('/reviews', data),
}

// ============================================================
// Analytics API (Admin)
// ============================================================
export const adminAnalyticsApi = {
  getDashboard: () => http.get('/analytics/dashboard'),
  getRfmSummary: () => http.get('/analytics/rfm/summary'),
  getClusteringDetail: () => http.get('/analytics/clustering/detail'),
  getSalesTrend: () => http.get('/analytics/sales/trend'),
  getSalesPrediction: () => http.get('/analytics/sales/prediction'),
  getSalesHeatmap: () => http.get('/analytics/sales/heatmap'),
  getPredictionMetrics: () => http.get('/analytics/sales/prediction-metrics'),
  getHotProducts: (params) => http.get('/analytics/products/hot', { params }),
  getAssociationList: (params) => http.get('/analytics/association/list', { params }),
  getChurnList: (params) => http.get('/analytics/churn/list', { params }),
  getChurnImportance: () => http.get('/analytics/churn/importance'),
  getChurnTrend: () => http.get('/analytics/churn/trend'),
  getModelMetrics: (params) => http.get('/analytics/metrics', { params }),
  getModelViz: (model) => http.get(`/analytics/viz/${model}`),
  recompute: () => http.post('/analytics/admin/recompute', {}),
  getLastComputeTime: () => http.get('/analytics/admin/last-compute-time'),
  updateChurnStatus: (churnId, status) => http.put(`/analytics/churn/${churnId}/status`, { status }),
}

// ============================================================
// Admin API
// ============================================================
export const adminApi = {
  getProducts: (params) => http.get('/admin/products', { params }),
  getProduct: (id) => http.get(`/admin/products/${id}`),
  createProduct: (data) => http.post('/admin/products', data),
  updateProduct: (id, data) => http.put(`/admin/products/${id}`, data),
  toggleProductActive: (id) => http.put(`/admin/products/${id}/toggle-active`, {}),
  getOrders: (params) => http.get('/admin/orders', { params }),
  shipOrder: (id, tracking_number = '') => http.put(`/admin/orders/${id}/ship`, { tracking_number }),
  deliverOrder: (id) => http.put(`/admin/orders/${id}/deliver`, {}),
  refundOrder: (id) => http.post(`/admin/orders/${id}/refund`, {}),
  payOrder: (id) => http.post(`/admin/orders/${id}/pay`, {}),
  getUsers: (params) => http.get('/admin/users', { params }),
  adjustBalance: (userId, amount) => http.put(`/admin/users/${userId}/balance`, { amount }),
  resetSystem: (mode) => http.post('/admin/reset', { mode }),
  importData: () => http.post('/admin/import-data', {}),
}

// ============================================================
// Upload API
// ============================================================
export const uploadApi = {
  upload: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default http
