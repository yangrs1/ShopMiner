<template>
  <div class="order-detail-page">
    <div class="page-card">
      <div class="detail-header">
        <el-button @click="$router.back()" text><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2>订单详情</h2>
      </div>

      <!-- Order Info Header -->
      <div class="order-info-bar">
        <div class="order-number">订单号: #{{ order.id }}</div>
        <el-tag :type="statusType(order.status)" size="large">{{ statusLabel(order.status) }}</el-tag>
        <span class="order-time">创建时间: {{ order.created_at }}</span>
      </div>

      <!-- Product List -->
      <div class="section">
        <h3>商品信息</h3>
        <el-table :data="order.items" stripe>
          <el-table-column label="商品" min-width="300">
            <template #default="{ row }">
              <div class="product-cell">
                <img :src="row.product_image || '/static/default-product.png'" class="product-thumb" />
                <span>{{ row.product_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="unit_price" label="单价" width="120" align="right">
            <template #default="{ row }">¥{{ (row.unit_price / 100).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="80" align="center" />
          <el-table-column label="小计" width="120" align="right">
            <template #default="{ row }">¥{{ (row.unit_price * row.quantity / 100).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Amount Summary -->
      <div class="section amount-summary">
        <div class="amount-row"><span>商品总额</span><span>¥{{ ((order.total_amount - order.freight) / 100).toFixed(2) }}</span></div>
        <div class="amount-row"><span>运费</span><span>¥{{ (order.freight / 100).toFixed(2) }}</span></div>
        <div class="amount-row total"><span>合计</span><span>¥{{ (order.total_amount / 100).toFixed(2) }}</span></div>
      </div>

      <!-- Shipping Info -->
      <div class="section" v-if="order.shipping_address">
        <h3>收货信息</h3>
        <div class="info-row"><span class="label">地址</span><span>{{ order.shipping_address }}</span></div>
        <div class="info-row"><span class="label">电话</span><span>{{ order.shipping_phone }}</span></div>
        <div class="info-row" v-if="order.tracking_number"><span class="label">运单号</span><span>{{ order.tracking_number }}</span></div>
      </div>

      <!-- Status Timeline -->
      <div class="section" v-if="order.status_logs && order.status_logs.length">
        <h3>订单状态</h3>
        <el-timeline>
          <el-timeline-item
            v-for="log in order.status_logs"
            :key="log.id"
            :timestamp="log.created_at"
            :type="timelineType(log.to_status)"
          >
            {{ statusLabel(log.to_status) }}
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- Action Buttons -->
      <div class="section action-bar" v-if="actionVisible">
        <el-button v-if="order.status === 'pending'" type="primary" @click="payOrder" :loading="loading">立即付款</el-button>
        <el-button v-if="order.status === 'pending'" type="danger" @click="cancelOrder" :loading="loading">取消订单</el-button>
        <el-button v-if="order.status === 'shipped'" type="success" @click="confirmDelivery" :loading="loading">确认收货</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const order = ref({ items: [], status_logs: [] })
const loading = ref(false)

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
function timelineType(s) { return s === 'delivered' ? 'success' : s === 'shipped' ? 'primary' : s === 'paid' ? '' : 'info' }

const actionVisible = computed(() => ['pending', 'shipped'].includes(order.value.status))

async function loadOrder() {
  try {
    const res = await orderApi.getOrder(route.params.id)
    order.value = res.data || {}
  } catch { ElMessage.error('加载订单失败') }
}

async function payOrder() {
  loading.value = true
  try {
    await ElMessageBox.confirm('确认使用余额支付？', '支付')
    await orderApi.payOrder(order.value.id)
    ElMessage.success('支付成功')
    loadOrder()
  } catch {} finally { loading.value = false }
}

async function cancelOrder() {
  loading.value = true
  try {
    await ElMessageBox.confirm('确认取消此订单？', '取消订单')
    await orderApi.cancelOrder(order.value.id)
    ElMessage.success('订单已取消')
    loadOrder()
  } catch {} finally { loading.value = false }
}

async function confirmDelivery() {
  loading.value = true
  try {
    await ElMessageBox.confirm('确认已收到商品？', '确认收货')
    await orderApi.confirmDelivery(order.value.id)
    ElMessage.success('已确认收货')
    loadOrder()
  } catch {} finally { loading.value = false }
}

onMounted(loadOrder)
</script>

<style scoped>
.order-detail-page { max-width: 900px; margin: 0 auto; padding: 20px; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.detail-header h2 { margin: 0; }
.order-info-bar { display: flex; align-items: center; gap: 16px; padding: 16px; background: #f5f7fa; border-radius: 8px; margin-bottom: 20px; }
.order-number { font-weight: 600; font-size: 15px; }
.order-time { font-size: 12px; color: #909399; margin-left: auto; }
.section { margin-bottom: 24px; }
.section h3 { margin-bottom: 12px; font-size: 15px; }
.product-cell { display: flex; align-items: center; gap: 10px; }
.product-thumb { width: 50px; height: 50px; object-fit: cover; border-radius: 4px; background: #f0f0f0; }
.amount-summary { max-width: 360px; margin-left: auto; }
.amount-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }
.amount-row.total { font-size: 18px; font-weight: 700; border-top: 1px solid #dcdfe6; padding-top: 8px; margin-top: 4px; color: #e6a23c; }
.info-row { display: flex; gap: 12px; padding: 4px 0; font-size: 14px; }
.info-row .label { color: #909399; min-width: 60px; }
.action-bar { display: flex; gap: 12px; justify-content: flex-end; }
</style>
