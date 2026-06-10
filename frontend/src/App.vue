<template>
  <div id="shopminer-app">
    <NavBar />
    <main class="main-container">
      <router-view v-slot="{ Component }">
        <transition name="el-fade-in-linear" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <footer class="app-footer">
      <div class="footer-content">
        &copy; 2026 <strong>ShopMiner</strong> — 基于数据挖掘的智能电商平台
      </div>
    </footer>
  </div>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
</script>
