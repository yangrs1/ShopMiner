<template>
  <div class="favorites-page">
    <div class="page-card">
      <h2 class="page-title">
        <el-icon><StarFilled /></el-icon> 我的收藏
        <span class="fav-count" v-if="total">（共 {{ total }} 件）</span>
      </h2>

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

      <el-row :gutter="16" v-else-if="favorites.length">
        <el-col :xs="12" :sm="8" :md="6" v-for="fav in favorites" :key="fav.id">
          <div class="fav-item">
            <ProductCard :product="fav.product" />
            <div class="fav-actions">
              <el-button type="danger" size="small" plain @click="confirmRemove(fav)">
                <el-icon><Delete /></el-icon> 取消收藏
              </el-button>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="mt-md"
        @current-change="loadFavorites"
      />

      <div v-else class="empty-state">
        <el-icon style="font-size: 48px; color: var(--text-placeholder); margin-bottom: 12px">
          <Star />
        </el-icon>
        <p>还没有收藏任何商品</p>
        <p style="font-size: 13px; color: var(--text-secondary)">去 <router-link :to="{ name: 'Home' }" style="color: var(--color-primary)">首页</router-link> 看看心仪的商品吧</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Star, StarFilled, Delete } from '@element-plus/icons-vue'
import { favoriteApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProductCard from '../components/ProductCard.vue'

const favorites = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const perPage = 20

async function loadFavorites() {
  loading.value = true
  try {
    const res = await favoriteApi.list({ page: page.value, per_page: perPage })
    favorites.value = (res.data.favorites || []).filter(f => f.product && f.product.is_active)
    total.value = res.data.total || 0
  } catch {
    favorites.value = []
  } finally {
    loading.value = false
  }
}

async function confirmRemove(fav) {
  try {
    await ElMessageBox.confirm(
      `确定从收藏中移除「${fav.product.name}」吗？`,
      '取消收藏',
      { confirmButtonText: '确认移除', cancelButtonText: '再看看', type: 'warning' }
    )
    await favoriteApi.remove(fav.product_id)
    favorites.value = favorites.value.filter(f => f.id !== fav.id)
    ElMessage.success('已移除收藏')
  } catch {
    // cancelled
  }
}

onMounted(loadFavorites)
</script>

<style scoped>
.fav-count {
  font-size: 14px;
  font-weight: normal;
  color: var(--text-secondary);
  margin-left: 8px;
}
.fav-item {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.fav-actions {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.favorites-page .el-pagination {
  justify-content: center;
  margin-top: 20px;
}
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}
</style>
