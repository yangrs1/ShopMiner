<template>
  <div class="cart-page">
    <div class="page-card">
      <h2 class="page-title">购物车</h2>
      <div v-if="loading">
        <el-skeleton :count="3" animated :throttle="{ leading: 500, trailing: 300 }">
          <template #template>
            <div class="cart-item">
              <el-skeleton-item variant="image" style="width: 80px; height: 80px; border-radius: var(--border-radius-sm)" />
              <div class="cart-item-info">
                <el-skeleton-item variant="h3" style="width: 50%; margin-bottom: 8px" />
                <el-skeleton-item variant="text" style="width: 30%" />
              </div>
              <el-skeleton-item variant="text" style="width: 120px; height: 32px" />
              <el-skeleton-item variant="text" style="width: 60px" />
              <el-skeleton-item variant="button" style="width: 32px; height: 32px" />
            </div>
          </template>
        </el-skeleton>
      </div>
      <div v-else-if="items.length">
        <div v-for="item in items" :key="item.id" class="cart-item">
          <img :src="item.image || '/static/images/default/placeholder_1.jpg'" class="cart-item-img" @error="e => e.target.src='/static/images/default/placeholder_1.jpg'" />
          <div class="cart-item-info">
            <h4>{{ item.name }}</h4>
            <span class="price" style="font-size: 16px">{{ (item.price / 100).toFixed(2) }}</span>
          </div>
          <el-input-number v-model="item.quantity" :min="1" :max="item.stock || 99" size="small"
            @change="updateItem(item)" />
          <span class="cart-item-subtotal price" style="font-size: 16px">
            {{ (item.price * item.quantity / 100).toFixed(2) }}
          </span>
          <el-button type="danger" text @click="removeItem(item.product_id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="cart-footer">
          <div class="cart-summary-row">
            <span>共 {{ totalItems }} 件商品</span>
            <span>合计: <span class="price">{{ (totalAmount / 100).toFixed(2) }}</span></span>
          </div>
          <div class="cart-balance-row">
            <span>账户余额: <strong :class="balanceEnough ? 'balance-ok' : 'balance-low'">{{ (userBalance / 100).toFixed(2) }}</strong></span>
            <span v-if="!balanceEnough" class="balance-warn">余额不足，请先充值</span>
            <span v-else class="balance-hint">下单后需在订单页完成付款</span>
          </div>
          <el-button type="primary" @click="checkout" :loading="checkingOut">
            结算
          </el-button>
        </div>
      </div>
      <div v-else class="empty-state">购物车是空的</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Delete } from '@element-plus/icons-vue'
import { cartApi, orderApi } from '../api'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const items = ref([])
const loading = ref(false)
const checkingOut = ref(false)

const totalItems = computed(() => items.value.reduce((s, i) => s + i.quantity, 0))
const totalAmount = computed(() => items.value.reduce((s, i) => s + i.price * i.quantity, 0))
const userBalance = computed(() => userStore.currentUser?.balance || 0)
const balanceEnough = computed(() => userBalance.value >= totalAmount.value)

async function loadCart() {
  loading.value = true
  try {
    const res = await cartApi.getCart()
    items.value = res.data.items || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function updateItem(item) {
  const prevQuantity = item.quantity
  try {
    await cartApi.updateItem(item.product_id, item.quantity)
    await userStore.fetchCartCount()
  } catch {
    item.quantity = prevQuantity
    ElMessage.error('更新失败')
  }
}

async function removeItem(productId) {
  try {
    await cartApi.removeItem(productId)
    await loadCart()
    await userStore.fetchCartCount()
    ElMessage.success('已移除')
  } catch {
    // handled by interceptor
  }
}

async function checkout() {
  try {
    const { value: formData } = await ElMessageBox.prompt(
      '请确认收货信息',
      '确认订单',
      {
        confirmButtonText: '确认下单',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: `收货地址: ${userStore.currentUser?.address || '未设置，请先完善个人信息'}\n联系电话: ${userStore.currentUser?.phone || '未设置'}\n\n如需修改，请在输入框中填写：\n地址|电话`,
        inputValue: '',
        inputValidator: (val) => {
          if (!userStore.currentUser?.address && !val) {
            return '请先完善收货地址'
          }
          return true
        }
      }
    )
    let addr = userStore.currentUser?.address || ''
    let phone = userStore.currentUser?.phone || ''
    if (formData && formData.includes('|')) {
      const parts = formData.split('|')
      addr = parts[0].trim() || addr
      phone = parts[1]?.trim() || phone
    }
    checkingOut.value = true
    await orderApi.createOrder({ shipping_address: addr, shipping_phone: phone })
    ElMessage.success('订单已创建，请前往订单页付款')
    await userStore.fetchCartCount()
    router.push({ name: 'Orders' })
  } catch {
    // cancelled or error
  } finally {
    checkingOut.value = false
  }
}

onMounted(loadCart)
</script>

<style scoped>
.cart-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}
.cart-item:last-of-type {
  border-bottom: none;
}
.cart-item-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--border-radius-sm);
}
.cart-item-info {
  flex: 1;
}
.cart-item-info h4 {
  font-size: 14px;
  margin-bottom: 4px;
}
.cart-item-subtotal {
  min-width: 80px;
  text-align: right;
}
.cart-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 20px;
  margin-top: 12px;
  border-top: 2px solid var(--border-color);
}
.cart-summary-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 24px;
}
.cart-balance-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  font-size: 13px;
}
.balance-ok { color: #67C23A; }
.balance-low { color: #F56C6C; }
.balance-warn { color: #F56C6C; font-size: 12px; }
.balance-hint { color: var(--text-secondary); font-size: 12px; }
</style>
