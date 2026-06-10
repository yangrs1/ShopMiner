<template>
  <div class="register-page">
    <div class="register-card page-card">
      <h2 class="page-title text-center">注册 ShopMiner</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="姓" prop="last_name">
              <el-input v-model="form.last_name" placeholder="请输入姓" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="名" prop="first_name">
              <el-input v-model="form.first_name" placeholder="请输入名" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少8位，含大小写字母和数字" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item label="地址" prop="address">
          <el-input v-model="form.address" placeholder="请输入收货地址" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" native-type="submit">
            注册
          </el-button>
        </el-form-item>
      </el-form>
      <div class="register-footer">
        已有账号？<router-link :to="{ name: 'Login' }">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ first_name: '', last_name: '', email: '', password: '', address: '' })
const rules = {
  first_name: [{ required: true, message: '请输入名', trigger: 'blur' }],
  last_name: [{ required: true, message: '请输入姓', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, message: '密码需含大小写字母和数字', trigger: 'blur' },
  ],
  address: [{ required: true, message: '请输入地址', trigger: 'blur' }],
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.register(form)
    await userStore.fetchCartCount()
    ElMessage.success('注册成功')
    router.push({ name: 'Home' })
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
.register-card {
  width: 100%;
  max-width: 480px;
}
.register-footer {
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}
.register-footer a {
  color: var(--color-primary);
  text-decoration: none;
}
</style>
