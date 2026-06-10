<template>
  <div class="login-page">
    <div class="login-card page-card">
      <h2 class="page-title text-center">登录 ShopMiner</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" native-type="submit">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        还没有账号？<router-link :to="{ name: 'Register' }">立即注册</router-link>
      </div>
      <el-divider>测试账号</el-divider>
      <div class="login-hint">
        <p>管理员：<code>admin@shopminer.com</code> / <code>Admin@123</code></p>
        <p>普通用户：<code>customer@shopminer.com</code> / <code>Customer@123</code></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ email: '', password: '' })
const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(form.email, form.password)
    await userStore.fetchCartCount()
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/'
    await router.replace(redirect)
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
.login-card {
  width: 100%;
  max-width: 420px;
}
.login-footer {
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}
.login-footer a {
  color: var(--color-primary);
  text-decoration: none;
}
.login-hint {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.8;
}
.login-hint code {
  background: var(--bg-page);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--color-primary);
}
</style>
