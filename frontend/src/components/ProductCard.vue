<template>
  <el-card class="product-card" :body-style="{ padding: '0' }" @click="goDetail">
    <div class="product-image">
      <img :src="product.image || '/static/images/default/placeholder_1.jpg'" :alt="product.name" @error="onImgError" />
    </div>
    <div class="product-info">
      <h4 class="product-name">{{ product.name }}</h4>
      <p class="product-desc">{{ product.description }}</p>
      <div class="product-rating" v-if="avgRating !== null">
        <el-rate v-model="avgRating" disabled show-score size="small" score-template="{value}" />
        <span class="rating-count">({{ totalReviews }})</span>
      </div>
      <div class="product-rating" v-else>
        <span class="no-rating">暂无评价</span>
      </div>
      <div class="product-bottom">
        <span class="price">{{ (product.price / 100).toFixed(2) }}</span>
        <el-button type="primary" size="small" :disabled="product.stock === 0" @click.stop="handleAddCart">
          {{ product.stock === 0 ? '已售罄' : '加入购物车' }}
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { cartApi, productApi } from '../api'
import { ElMessage } from 'element-plus'

const props = defineProps({
  product: { type: Object, required: true },
})

const router = useRouter()
const userStore = useUserStore()
const avgRating = ref(null)
const totalReviews = ref(0)
let imgErrorCount = 0

onMounted(async () => {
  if (props.product?.id) {
    try {
      const res = await productApi.getProductRating(props.product.id)
      if (res.data) {
        avgRating.value = res.data.avg_rating || 0
        totalReviews.value = res.data.total_reviews || 0
      }
    } catch {} // silently fail, rating is optional
  }
})

function onImgError(e) {
  imgErrorCount++
  if (imgErrorCount > 1) {
    // 二次加载也失败，用纯色占位
    e.target.style.display = 'none'
    e.target.parentElement.classList.add('img-fallback')
    return
  }
  e.target.src = '/static/images/default/placeholder_1.jpg'
}

function goDetail() {
  router.push({ name: 'ProductDetail', params: { id: props.product.id } })
}

async function handleAddCart() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push({ name: 'Login' })
    return
  }
  try {
    await cartApi.addToCart(props.product.id, 1)
    await userStore.fetchCartCount()
    ElMessage.success('已加入购物车')
  } catch {
    // error handled by interceptor
  }
}
</script>

<style scoped>
.product-card {
  cursor: pointer;
  transition: box-shadow var(--transition-normal), transform var(--transition-normal);
  border: none;
}
.product-card:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-2px);
}
.product-image {
  width: 100%;
  height: 200px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.product-image.img-fallback::after {
  content: '暂无图片';
  color: #c0c4cc;
  font-size: 14px;
}
.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-slow);
}
.product-card:hover .product-image img {
  transform: scale(1.05);
}
.product-info {
  padding: 12px 16px 16px;
}
.product-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}
.product-desc {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 12px;
}
.product-rating {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 16px 8px;
}
.rating-count {
  font-size: 12px;
  color: var(--text-secondary);
}
.no-rating {
  font-size: 12px;
  color: #c0c4cc;
}
.product-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
