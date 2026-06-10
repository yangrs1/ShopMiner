<template>
  <div class="orders-page">
    <div class="page-card">
      <h2 class="page-title">我的订单</h2>
      <div v-if="orders.length">
        <div v-for="order in orders" :key="order.id" class="order-item page-card" style="margin-bottom: 12px">
          <div class="order-header">
            <span class="order-id">订单 #{{ order.id }}</span>
            <el-tag :type="statusType(order.status)" size="small">{{ statusLabel(order.status) }}</el-tag>
          </div>
          <div class="order-items">
            <div v-for="item in order.items" :key="item.id" class="order-product">
              <span>{{ item.product_name || '商品' + item.product_id }}</span>
              <span>x{{ item.quantity }}</span>
              <span class="price" style="font-size: 14px">{{ (item.unit_price * item.quantity / 100).toFixed(2) }}</span>
            </div>
          </div>
          <div class="order-footer">
            <span class="order-time">{{ order.created_at }}</span>
            <span>合计: <span class="price" style="font-size: 16px">{{ (order.total_amount / 100).toFixed(2) }}</span></span>
            <el-button v-if="order.status === 'pending'" type="primary" size="small" @click="payOrder(order.id)">
              付款
            </el-button>
            <el-button v-if="order.status === 'pending'" type="danger" size="small" @click="cancelOrder(order.id)">
              取消订单
            </el-button>
            <el-button size="small" @click="$router.push({ name: 'OrderDetail', params: { id: order.id } })">查看详情</el-button>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">暂无订单</div>
      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="mt-md"
        @current-change="loadOrders"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { orderApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const orders = ref([])
const page = ref(1)
const total = ref(0)
const perPage = 10

const statusMap = {
  pending: { label: '待付款', type: 'warning' },
  paid: { label: '已付款', type: 'primary' },
  shipped: { label: '已发货', type: '' },
  delivered: { label: '已送达', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  refunded: { label: '已退款', type: 'danger' },
}

function statusLabel(s) { return statusMap[s]?.label || s }
function statusType(s) { return statusMap[s]?.type || 'info' }

async function loadOrders() {
  try {
    const res = await orderApi.getOrders({ page: page.value, per_page: perPage })
    orders.value = res.data.orders || []
    total.value = res.data.total || 0
  } catch {
    orders.value = []
  }
}

async function cancelOrder(orderId) {
  try {
    await ElMessageBox.confirm('确认取消此订单？', '取消订单')
    await orderApi.cancelOrder(orderId)
    ElMessage.success('订单已取消')
    loadOrders()
  } catch {
    // cancelled or error
  }
}

async function payOrder(orderId) {
  try {
    await ElMessageBox.confirm('确认使用余额支付？', '支付')
    await orderApi.payOrder(orderId)
    ElMessage.success('支付成功')
    loadOrders()
  } catch {
    // cancelled or error
  }
}

onMounted(loadOrders)
</script>

<style scoped>
.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.order-id {
  font-weight: 600;
  font-size: 14px;
}
.order-items {
  padding: 8px 0;
}
.order-product {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  color: var(--text-regular);
}
.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}
.order-time {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
