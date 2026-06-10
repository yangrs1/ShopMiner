<template>
  <div class="category-nav" v-if="categories.length">
    <el-scrollbar>
      <div class="category-list">
        <div
          v-for="cat in categories"
          :key="cat.name"
          class="category-item"
          :class="{ active: activeCategory === cat.name }"
          @click="selectCategory(cat.name)"
        >
          <span class="category-name">{{ cat.name }}</span>
          <span class="category-count">（{{ cat.count }}件）</span>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { productApi } from '../api'

const props = defineProps({
  activeCategory: { type: String, default: '' },
})

const emit = defineEmits(['select'])
const categories = ref([])

onMounted(async () => {
  try {
    const res = await productApi.getCategories()
    categories.value = res.data.categories || []
  } catch {
    categories.value = []
  }
})

function selectCategory(name) {
  emit('select', name)
}
</script>

<style scoped>
.category-nav {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 20px;
}
.category-list {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
.category-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 20px;
  background: var(--bg-page);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  font-size: 14px;
}
.category-item:hover {
  background: var(--color-primary-light);
  color: #fff;
}
.category-item.active {
  background: var(--color-primary);
  color: #fff;
}
.category-name {
  font-weight: 500;
}
.category-count {
  font-size: 12px;
  opacity: 0.7;
}
</style>
