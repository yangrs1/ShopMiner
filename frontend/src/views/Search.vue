<template>
  <div class="search-page">
    <div class="page-card">
      <h2 class="page-title">搜索结果: "{{ query }}"</h2>
      <div class="filter-bar">
        <div class="filter-row">
          <el-input v-model="filterMinPrice" placeholder="最低价" class="filter-price" size="small" type="number" min="0" @input="applyFilters">
            <template #prefix>¥</template>
          </el-input>
          <span class="filter-separator">—</span>
          <el-input v-model="filterMaxPrice" placeholder="最高价" class="filter-price" size="small" type="number" min="0" @input="applyFilters">
            <template #prefix>¥</template>
          </el-input>
          <el-select v-model="filterCategory" placeholder="品类" clearable class="filter-select" size="small" @change="applyFilters">
            <el-option v-for="cat in categories" :key="cat.name" :label="cat.name" :value="cat.name" />
          </el-select>
          <el-select v-model="filterSort" placeholder="排序" class="filter-select" size="small" @change="applyFilters">
            <el-option label="综合排序" value="" />
            <el-option label="价格 ↑" value="price_asc" />
            <el-option label="价格 ↓" value="price_desc" />
            <el-option label="评分 ↓" value="rating_desc" />
            <el-option label="最新" value="created_at_desc" />
          </el-select>
          <el-button size="small" @click="resetFilters">重置</el-button>
        </div>
      </div>
      <el-row :gutter="16" v-if="products.length">
        <el-col :xs="12" :sm="8" :md="6" v-for="p in products" :key="p.id">
          <ProductCard :product="p" />
        </el-col>
      </el-row>
      <div v-else-if="!loading" class="empty-state">未找到相关商品</div>
      <div v-if="loading" class="skeleton-grid">
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
      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="mt-md"
        @current-change="search"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productApi } from '../api'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const products = ref([])
const query = ref('')
const page = ref(1)
const total = ref(0)
const perPage = 20
const loading = ref(false)
const categories = ref([])
const filterMinPrice = ref('')
const filterMaxPrice = ref('')
const filterCategory = ref('')
const filterSort = ref('')

async function search() {
  if (!query.value) return
  loading.value = true
  try {
    const params = {
      q: query.value,
      page: page.value,
      per_page: perPage,
    }
    if (filterMinPrice.value) params.min_price = Math.round(parseFloat(filterMinPrice.value) * 100)
    if (filterMaxPrice.value) params.max_price = Math.round(parseFloat(filterMaxPrice.value) * 100)
    if (filterCategory.value) params.category = filterCategory.value
    if (filterSort.value) {
      const [sort_by, order] = filterSort.value.split('_')
      params.sort_by = sort_by
      params.order = order
    }
    const res = await productApi.getProducts(params)
    products.value = res.data.products || []
    total.value = res.data.total || 0
  } catch {
    products.value = []
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await productApi.getCategories()
    categories.value = res.data.categories || []
  } catch {
    categories.value = []
  }
}

function applyFilters() {
  page.value = 1
  search()
  router.replace({ query: { ...route.query, min_price: filterMinPrice.value || undefined, max_price: filterMaxPrice.value || undefined, category: filterCategory.value || undefined, sort: filterSort.value || undefined } })
}

function resetFilters() {
  filterMinPrice.value = ''
  filterMaxPrice.value = ''
  filterCategory.value = ''
  filterSort.value = ''
  page.value = 1
  search()
  router.replace({ query: { ...route.query, min_price: undefined, max_price: undefined, category: undefined, sort: undefined } })
}

watch(() => route.query.q, (newQ) => {
  if (newQ) {
    query.value = newQ
    filterMinPrice.value = route.query.min_price || ''
    filterMaxPrice.value = route.query.max_price || ''
    filterCategory.value = route.query.category || ''
    filterSort.value = route.query.sort || ''
    page.value = 1
    search()
  }
}, { immediate: true })

loadCategories()
</script>

<style scoped>
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
.filter-bar {
  margin-bottom: 16px;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-price {
  width: 110px;
}
.filter-select {
  width: 140px;
}
.filter-separator {
  color: var(--text-secondary);
}
</style>
