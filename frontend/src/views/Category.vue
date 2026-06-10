<template>
  <div class="category-page">
    <div class="page-card">
      <h2 class="page-title">{{ categoryName }}</h2>
      <div class="filter-bar">
        <div class="filter-row">
          <el-input v-model="filterMinPrice" placeholder="最低价" class="filter-price" size="small" type="number" min="0" @input="applyFilters">
            <template #prefix>¥</template>
          </el-input>
          <span class="filter-separator">—</span>
          <el-input v-model="filterMaxPrice" placeholder="最高价" class="filter-price" size="small" type="number" min="0" @input="applyFilters">
            <template #prefix>¥</template>
          </el-input>
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
      <div v-else-if="!loading" class="empty-state">该分类暂无商品</div>
      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="mt-md"
        @current-change="loadProducts"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { productApi } from '../api'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const products = ref([])
const categoryName = ref('')
const page = ref(1)
const total = ref(0)
const perPage = 20
const loading = ref(false)
const filterMinPrice = ref('')
const filterMaxPrice = ref('')
const filterSort = ref('')

async function loadProducts() {
  loading.value = true
  try {
    const params = {
      category: categoryName.value,
      page: page.value,
      per_page: perPage,
    }
    if (filterMinPrice.value) params.min_price = Math.round(parseFloat(filterMinPrice.value) * 100)
    if (filterMaxPrice.value) params.max_price = Math.round(parseFloat(filterMaxPrice.value) * 100)
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

function applyFilters() {
  page.value = 1
  loadProducts()
}

function resetFilters() {
  filterMinPrice.value = ''
  filterMaxPrice.value = ''
  filterSort.value = ''
  page.value = 1
  loadProducts()
}

watch(() => route.params.name, (name) => {
  if (name) {
    categoryName.value = name
    page.value = 1
    loadProducts()
  }
}, { immediate: true })
</script>

<style scoped>
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
