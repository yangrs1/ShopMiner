<template>
  <div class="home-page">
    <!-- Banner -->
    <div class="banner page-card">
      <h1 class="banner-title">ShopMiner</h1>
      <p class="banner-subtitle">基于数据挖掘的智能电商平台</p>
      <el-button type="primary" size="large" @click="scrollToProducts">
        探索商品
      </el-button>
    </div>

    <!-- Category Navigation -->
    <CategoryNav :active-category="activeCategory" @select="selectCategory" />

    <!-- Hot Products -->
    <div class="section">
      <h3 class="section-title">
        <el-icon><TrendCharts /></el-icon>
        {{ activeCategory ? activeCategory + ' · 热门推荐' : '热门推荐' }}
      </h3>
      <el-row :gutter="16" v-if="products.length">
        <el-col :xs="12" :sm="8" :md="6" v-for="p in products" :key="p.id">
          <ProductCard :product="p" />
        </el-col>
      </el-row>
      <div v-else-if="loading" class="skeleton-grid">
        <el-skeleton :count="4" animated :throttle="{ leading: 500, trailing: 300 }">
          <template #template>
            <div class="skeleton-card">
              <el-skeleton-item variant="image" style="width: 100%; height: 180px" />
              <div style="padding: 12px">
                <el-skeleton-item variant="h3" style="width: 60%; margin-bottom: 8px" />
                <el-skeleton-item variant="text" style="width: 90%; margin-bottom: 4px" />
                <el-skeleton-item variant="text" style="width: 40%" />
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>
      <div v-else class="empty-state">暂无商品</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { TrendCharts } from '@element-plus/icons-vue'
import { analyticsApi, productApi } from '../api'
import ProductCard from '../components/ProductCard.vue'
import CategoryNav from '../components/CategoryNav.vue'

const router = useRouter()
const products = ref([])
const activeCategory = ref('')
const loading = ref(false)

async function loadProducts(category) {
  loading.value = true
  try {
    // 先尝试热门推荐API
    const res = await analyticsApi.getHotProducts({ category: category || undefined, limit: 8 })
    products.value = res.data.products || []
  } catch {
    // fallback: 用商品列表API
    try {
      const res = await productApi.getProducts({ category: category || undefined, per_page: 8 })
      products.value = res.data.products || []
    } catch {
      products.value = []
    }
  } finally {
    loading.value = false
  }
}

function selectCategory(name) {
  activeCategory.value = activeCategory.value === name ? '' : name
  loadProducts(activeCategory.value)
}

function scrollToProducts() {
  const section = document.querySelector('.section')
  if (section) section.scrollIntoView({ behavior: 'smooth' })
}

onMounted(() => loadProducts())
</script>

<style scoped>
.banner {
  text-align: center;
  padding: 48px 24px;
  background: linear-gradient(135deg, #409EFF 0%, #66B1FF 100%);
  color: #fff;
  border-radius: var(--border-radius);
  margin-bottom: 20px;
}
.banner-title {
  font-family: var(--font-heading);
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #fff;
}
.banner-subtitle {
  font-size: 16px;
  opacity: 0.9;
  margin-bottom: 20px;
}
.banner .el-button {
  background: rgba(255,255,255,0.2);
  border-color: rgba(255,255,255,0.4);
  color: #fff;
}
.banner .el-button:hover {
  background: rgba(255,255,255,0.3);
}
.section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}
</style>
