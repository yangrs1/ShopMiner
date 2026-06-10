<template>
  <el-menu mode="horizontal" :ellipsis="false" class="navbar">
    <el-menu-item @click="router.push({ name: 'Home' })" class="navbar-brand">
      <strong class="brand-text">ShopMiner</strong>
    </el-menu-item>

    <div class="navbar-search">
      <el-input
        v-model="searchQuery"
        placeholder="搜索商品..."
        :prefix-icon="Search"
        @keyup.enter="doSearch"
        clearable
        size="default"
      />
    </div>

    <div class="navbar-spacer" />

    <el-menu-item @click="router.push({ name: 'Home' })">
      <el-icon><HomeFilled /></el-icon> 首页
    </el-menu-item>

    <template v-if="userStore.isLoggedIn">
      <el-menu-item @click="router.push({ name: 'Cart' })">
        <el-icon><ShoppingCart /></el-icon> 购物车
        <el-badge v-if="userStore.cartCount > 0" :value="userStore.cartCount" :max="99" class="cart-badge" />
      </el-menu-item>
      <el-menu-item @click="router.push({ name: 'Orders' })">
        <el-icon><Document /></el-icon> 订单
      </el-menu-item>
      <el-menu-item @click="router.push({ name: 'Favorites' })">
        <el-icon><Star /></el-icon> 收藏
      </el-menu-item>
      <el-menu-item v-if="userStore.isAdmin" @click="router.push({ name: 'Admin' })">
        <el-icon><Setting /></el-icon> 管理
      </el-menu-item>

      <el-sub-menu index="user-menu">
        <template #title>
          <el-icon><User /></el-icon> {{ userStore.displayName }}
        </template>
        <el-menu-item @click="router.push({ name: 'Profile' })">
          <el-icon><DataAnalysis /></el-icon> 消费报告
        </el-menu-item>
        <el-menu-item @click="userStore.logout()">
          <el-icon><SwitchButton /></el-icon> 退出登录
        </el-menu-item>
      </el-sub-menu>
    </template>

    <template v-else>
      <el-menu-item @click="router.push({ name: 'Login' })">登录</el-menu-item>
      <el-menu-item @click="router.push({ name: 'Register' })">注册</el-menu-item>
    </template>
  </el-menu>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, HomeFilled, ShoppingCart, Document, Setting, User, DataAnalysis, SwitchButton, Star } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const searchQuery = ref('')

function doSearch() {
  const q = searchQuery.value.trim()
  if (q) {
    router.push({ name: 'Search', query: { q } })
  }
}
</script>

<style scoped>
.navbar {
  padding: 0 24px;
  align-items: center;
  background: var(--bg-card);
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}
.brand-text {
  font-family: var(--font-heading);
  font-size: 20px;
  color: var(--color-primary);
  letter-spacing: -0.5px;
}
.navbar-search {
  width: 320px;
  margin: 0 20px;
}
.navbar-spacer {
  flex: 1;
}
.cart-badge {
  margin-left: 6px;
}
</style>
