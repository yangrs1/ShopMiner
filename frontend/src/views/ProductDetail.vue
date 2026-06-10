<template>
  <div class="detail-page" v-if="loading">
    <el-row :gutter="24">
      <el-col :sm="10" :md="8">
        <div class="detail-image page-card" style="padding: 0; overflow: hidden">
          <el-skeleton animated :throttle="{ leading: 500, trailing: 300 }">
            <template #template>
              <el-skeleton-item variant="image" style="width: 100%; height: 400px" />
            </template>
          </el-skeleton>
        </div>
      </el-col>
      <el-col :sm="14" :md="16">
        <div class="detail-info page-card">
          <el-skeleton :rows="4" animated :throttle="{ leading: 500, trailing: 300 }" />
        </div>
      </el-col>
    </el-row>
  </div>
  <div class="detail-page" v-else-if="product">
    <el-row :gutter="24">
      <!-- Product Image -->
      <el-col :sm="10" :md="8">
        <div class="detail-image page-card">
          <img :src="product.image || '/static/images/default/placeholder_1.jpg'" :alt="product.name" @error="onImgError" />
        </div>
      </el-col>
      <!-- Product Info -->
      <el-col :sm="14" :md="16">
        <div class="detail-info page-card">
          <div class="detail-name-row">
            <h2 class="detail-name">{{ product.name }}</h2>
            <el-button
              :icon="isFavorited ? StarFilled : Star"
              :type="isFavorited ? 'danger' : 'default'"
              :loading="favoriteLoading"
              circle
              size="large"
              class="favorite-btn"
              :title="isFavorited ? '取消收藏' : '加入收藏'"
              @click="toggleFavorite"
            />
          </div>
          <p class="detail-desc">{{ product.description }}</p>
          <div class="detail-meta">
            <span class="price">{{ (product.price / 100).toFixed(2) }}</span>
            <el-tag v-if="product.stock > 0" type="success">有货 ({{ product.stock }})</el-tag>
            <el-tag v-else type="danger">缺货</el-tag>
          </div>
          <div class="detail-rating" v-if="ratingSummary">
            <el-rate v-model="ratingSummary.avg_rating" disabled show-score size="large" score-template="{value} 分" />
            <span class="rating-total">{{ ratingSummary.total_reviews }} 条评价</span>
          </div>
          <div class="detail-actions">
            <el-input-number v-model="quantity" :min="1" :max="product.stock || 99" />
            <el-button type="primary" :disabled="product.stock === 0" @click="addToCart">
              加入购物车
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Association Recommendations -->
    <div class="section" v-if="recommendations.length">
      <h3 class="section-title">
        <el-icon><Connection /></el-icon> 关联推荐
        <el-tag size="small" type="info" effect="plain" style="margin-left: 8px">
          基于 FP-Growth 关联规则挖掘
        </el-tag>
      </h3>
      <el-row :gutter="16">
        <el-col :xs="12" :sm="8" :md="6" v-for="r in recommendations" :key="r.product.id">
          <div class="rec-card">
            <ProductCard :product="r.product" />
            <div class="rec-reason" v-if="r.reason">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ r.reason }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Reviews -->
    <div class="section">
      <h3 class="section-title">
        <el-icon><Star /></el-icon> 商品评价
        <el-rate v-model="reviewForm.rating" style="margin-left: 16px" v-if="userStore.isLoggedIn" />
        <el-button v-if="userStore.isLoggedIn" size="small" type="primary" @click="submitReview" :loading="submittingReview" style="margin-left: 8px">
          发表评价
        </el-button>
      </h3>
      <div class="page-card" v-if="reviews.length">
        <div v-for="r in reviews" :key="r.id" class="review-item">
          <div class="review-header">
            <el-rate v-model="r.rating" disabled show-score size="small" />
            <span class="review-user">{{ r.user_name }}</span>
            <span class="review-time">{{ r.created_at?.slice(0, 10) }}</span>
          </div>
          <p class="review-content" v-if="r.content">{{ r.content }}</p>
        </div>
      </div>
      <div v-else class="empty-state" style="padding: 20px">暂无评价，快来第一个评价吧</div>
    </div>
  </div>
  <div v-else class="empty-state">商品不存在</div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Connection, Star, StarFilled, InfoFilled } from '@element-plus/icons-vue'
import { productApi, analyticsApi, cartApi, favoriteApi } from '../api'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const userStore = useUserStore()
const product = ref(null)
const loading = ref(false)
const quantity = ref(1)
const recommendations = ref([])
const reviews = ref([])
const submittingReview = ref(false)
const reviewForm = ref({ rating: 5, content: '' })
const ratingSummary = ref(null)
const isFavorited = ref(false)
const favoriteLoading = ref(false)

function onImgError(e) {
  e.target.src = '/static/images/default/placeholder_1.jpg'
  e.target.onerror = null
}

async function loadProduct() {
  loading.value = true
  try {
    const res = await productApi.getProduct(route.params.id)
    product.value = res.data
  } catch {
    product.value = null
  } finally {
    loading.value = false
  }
}

async function loadRecommendations() {
  try {
    const res = await analyticsApi.getAssociationForProduct(route.params.id)
    recommendations.value = res.data.recommendations || []
  } catch {
    recommendations.value = []
  }
}

async function loadFavoriteStatus() {
  if (!userStore.isLoggedIn) {
    isFavorited.value = false
    return
  }
  try {
    const res = await favoriteApi.check(product.value.id)
    isFavorited.value = res.data.favorited
  } catch {
    isFavorited.value = false
  }
}

async function toggleFavorite() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  favoriteLoading.value = true
  try {
    if (isFavorited.value) {
      await favoriteApi.remove(product.value.id)
      isFavorited.value = false
      ElMessage.success('已取消收藏')
    } else {
      await favoriteApi.add(product.value.id)
      isFavorited.value = true
      ElMessage.success('已加入收藏')
    }
  } catch {
    // handled by interceptor
  } finally {
    favoriteLoading.value = false
  }
}

async function addToCart() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  try {
    await cartApi.addToCart(product.value.id, quantity.value)
    await userStore.fetchCartCount()
    ElMessage.success('已加入购物车')
  } catch {
    // handled by interceptor
  }
}

async function loadRating() {
  try {
    const res = await productApi.getProductRating(route.params.id)
    if (res.data && res.data.total_reviews > 0) {
      ratingSummary.value = res.data
    } else {
      ratingSummary.value = null
    }
  } catch {
    ratingSummary.value = null
  }
}

async function loadReviews() {
  try {
    const res = await analyticsApi.getReviews(route.params.id)
    reviews.value = res.data.reviews || []
  } catch {
    reviews.value = []
  }
}

async function submitReview() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  submittingReview.value = true
  try {
    await analyticsApi.createReview({
      product_id: product.value.id,
      rating: reviewForm.value.rating,
    })
    ElMessage.success('评价成功')
    reviewForm.value.rating = 5
    loadReviews()
  } catch {
    // handled by interceptor
  } finally {
    submittingReview.value = false
  }
}

onMounted(async () => {
  await loadProduct()
  if (product.value) {
    loadFavoriteStatus()
    loadRating()
  }
  loadRecommendations()
  loadReviews()
})

watch(() => route.params.id, async (newId) => {
  if (newId) {
    isFavorited.value = false
    await loadProduct()
    if (product.value) {
      loadFavoriteStatus()
      loadRating()
    }
    loadRecommendations()
    loadReviews()
  }
})
</script>

<style scoped>
.detail-image {
  padding: 0;
  overflow: hidden;
}
.detail-image img {
  width: 100%;
  height: 400px;
  object-fit: cover;
}
.detail-name-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.detail-name {
  font-size: 24px;
  font-weight: 600;
  flex: 1;
  margin: 0;
}
.favorite-btn {
  flex-shrink: 0;
}
.detail-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
  line-height: 1.6;
}
.detail-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.detail-rating {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}
.rating-total {
  font-size: 14px;
  color: var(--text-secondary);
}
.detail-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.section {
  margin-top: 24px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}
.review-item:last-child { border-bottom: none; }
.review-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.review-user { color: var(--text-secondary); font-size: 13px; }
.review-time { color: var(--text-secondary); font-size: 12px; margin-left: auto; }
.review-content {
  color: var(--text-primary);
  font-size: 14px;
  margin: 4px 0 0 0;
  padding-left: 24px;
}
.rec-card {
  height: 100%;
}
.rec-reason {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  margin-top: 8px;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f9ff 100%);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--border-radius-sm);
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-regular);
}
.rec-reason .el-icon {
  color: var(--color-primary);
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
