<template>
  <div class="product-management">
    <h2 class="page-title">商品管理</h2>
    <div class="kpi-card">
      <!-- Toolbar -->
      <div class="card-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="search"
            placeholder="搜索商品名称..."
            clearable
            size="default"
            style="width: 260px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
        <div class="toolbar-right">
          <el-button type="success" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新增商品
          </el-button>
        </div>
      </div>

      <!-- Product Table -->
      <el-table :data="products" stripe v-loading="loading" empty-text="暂无商品数据" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column label="图片" width="80" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image"
              :src="row.image"
              style="width: 60px; height: 60px; border-radius: 6px; object-fit: cover; display: block;"
              fit="cover"
              :preview-src-list="[row.image]"
              preview-teleported
            >
              <template #error>
                <div class="image-placeholder">无图</div>
              </template>
            </el-image>
            <div v-else class="image-placeholder">无图</div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="价格" width="120" align="right">
          <template #default="{ row }">{{ fmtMoney(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="80" align="right" />
        <el-table-column prop="type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'digital' ? 'success' : 'primary'" size="small">
              {{ row.type === 'digital' ? '虚拟' : '实物' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="分类" width="110" show-overflow-tooltip />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '上架' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '下架' : '上架' }}
            </el-button>
            <el-button type="danger" size="small" @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev,pager,next"
        class="mt-md"
        @current-change="loadProducts"
      />
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑商品' : '新增商品'"
      width="600px"
      :close-on-click-modal="false"
      destroy-on-close
      @close="closeDialog"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
        label-position="left"
        status-icon
      >
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商品名称" maxlength="200" />
        </el-form-item>

        <el-form-item label="商品描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入商品描述"
            maxlength="2000"
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="价格 (元)" prop="price">
              <el-input-number
                v-model="form.price"
                :min="0.01"
                :precision="2"
                :step="1"
                style="width: 100%"
                placeholder="请输入价格"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库存" prop="stock">
              <el-input-number
                v-model="form.stock"
                :min="0"
                :step="1"
                :precision="0"
                style="width: 100%"
                placeholder="请输入库存数量"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
                <el-option label="实物" value="physical" />
                <el-option label="虚拟" value="digital" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category_name">
              <el-input v-model="form.category_name" placeholder="请输入分类名称" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Image: Upload mode toggle -->
        <el-form-item label="商品图片" prop="image">
          <div class="image-upload-area">
            <div class="image-mode-toggle">
              <el-radio-group v-model="imageUploadType" size="small">
                <el-radio-button value="file">文件上传</el-radio-button>
                <el-radio-button value="url">URL输入</el-radio-button>
              </el-radio-group>
            </div>

            <!-- File upload mode -->
            <template v-if="imageUploadType === 'file'">
              <el-upload
                ref="uploadRef"
                :show-file-list="false"
                :auto-upload="true"
                :http-request="handleImageUpload"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                :before-upload="beforeImageUpload"
              >
                <el-button type="primary" :loading="uploading">
                  <el-icon><Upload /></el-icon>选择图片
                </el-button>
                <template #tip>
                  <div class="el-upload__tip" style="margin-top:4px">支持 jpg/png/gif/webp，不超过 2MB</div>
                </template>
              </el-upload>
            </template>

            <!-- URL input mode -->
            <template v-else>
              <el-input
                v-model="imageUrl"
                placeholder="输入图片 URL"
                style="width: 320px"
                @blur="handleImageUrlInput"
                @keyup.enter="handleImageUrlInput"
              >
                <template #append>
                  <el-button @click="handleImageUrlInput">确认</el-button>
                </template>
              </el-input>
            </template>

            <!-- Image preview -->
            <div v-if="imagePreview" class="image-preview-wrapper">
              <el-image
                :src="imagePreview"
                style="width: 120px; height: 120px; border-radius: 8px; object-fit: cover; margin-top: 8px;"
                fit="cover"
                :preview-src-list="[imagePreview]"
                preview-teleported
              />
              <el-button
                size="small"
                type="danger"
                text
                class="image-remove-btn"
                @click="removeImage"
              >
                移除
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false" :disabled="submitting">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存修改' : '创建商品' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Delete Confirmation Dialog -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="确认删除"
      width="400px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="delete-warning">
        <el-icon :size="40" color="#F56C6C" style="margin-bottom: 12px"><WarningFilled /></el-icon>
        <p>确定要删除商品 <strong>{{ deleteProductName }}</strong> 吗？</p>
        <p class="text-muted">该操作将商品设为下架状态（软删除），不会彻底删除数据。</p>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false" :disabled="deleting">取消</el-button>
        <el-button type="danger" @click="doDelete" :loading="deleting">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Plus, Upload, WarningFilled } from '@element-plus/icons-vue'
import { adminApi, uploadApi } from '../../api'
import { ElMessage } from 'element-plus'

// ============================================================
// State
// ============================================================
const products = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 15
const search = ref('')

// Dialog
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const submitting = ref(false)

// Image
const imageUploadType = ref('file')
const imagePreview = ref('')
const imageUrl = ref('')
const uploading = ref(false)
const uploadRef = ref(null)

// Delete
const deleteDialogVisible = ref(false)
const deleting = ref(false)
const deleteProductId = ref(null)
const deleteProductName = ref('')

// ============================================================
// Form Model
// ============================================================
const form = reactive({
  name: '',
  description: '',
  price: null,
  stock: null,
  type: 'physical',
  category_name: '',
  image: '',
})

// ============================================================
// Form Validation Rules
// ============================================================
const formRules = {
  name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 1, max: 200, message: '名称长度在 1-200 个字符', trigger: 'blur' },
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '价格必须大于 0', trigger: 'blur' },
  ],
  stock: [
    { required: true, message: '请输入库存', trigger: 'blur' },
    { type: 'number', min: 0, message: '库存不能为负数', trigger: 'blur' },
  ],
  type: [
    { required: true, message: '请选择商品类型', trigger: 'change' },
  ],
  category_name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
  ],
}

// ============================================================
// Methods
// ============================================================
function fmtMoney(v) {
  if (v == null || isNaN(v)) return '-'
  return '¥' + Number(v / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadProducts() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: pageSize }
    if (search.value) params.name = search.value
    const res = await adminApi.getProducts(params)
    products.value = res.data.products || []
    total.value = res.data.total || 0
  } catch {
    products.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadProducts()
}

// --- Create Dialog ---
function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  dialogVisible.value = true

  // Pre-fill form
  form.name = row.name || ''
  form.description = row.description || ''
  form.price = row.price != null ? Number((row.price / 100).toFixed(2)) : null
  form.stock = row.stock != null ? row.stock : null
  form.type = row.type || 'physical'
  form.category_name = row.category_name || ''
  form.image = row.image || ''
  imagePreview.value = row.image || ''
  imageUrl.value = row.image || ''
}

function closeDialog() {
  dialogVisible.value = false
  resetForm()
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.price = null
  form.stock = null
  form.type = 'physical'
  form.category_name = ''
  form.image = ''
  imagePreview.value = ''
  imageUrl.value = ''
  imageUploadType.value = 'file'
  submitting.value = false
  formRef.value?.clearValidate()
}

// --- Image Handling ---
function beforeImageUpload(file) {
  const isImg = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)
  if (!isImg) {
    ElMessage.error('仅支持 jpg/png/gif/webp 格式的图片')
    return false
  }
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

async function handleImageUpload(options) {
  const file = options.file
  uploading.value = true
  try {
    const res = await uploadApi.upload(file)
    const url = res.data?.url || res.data || ''
    if (url) {
      form.image = url
      imagePreview.value = url
      ElMessage.success('图片上传成功')
    } else {
      ElMessage.warning('上传响应缺少图片 URL，请检查')
    }
  } catch {
    ElMessage.error('图片上传失败')
  } finally {
    uploading.value = false
  }
}

function handleImageUrlInput() {
  const url = imageUrl.value.trim()
  if (!url) {
    ElMessage.warning('请输入图片 URL')
    return
  }
  form.image = url
  imagePreview.value = url
}

function removeImage() {
  form.image = ''
  imagePreview.value = ''
  imageUrl.value = ''
}

// --- Submit ---
async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    // Convert price from yuan (display) to fen (storage)
    const data = {
      name: form.name,
      description: form.description,
      price: Math.round(form.price * 100),
      stock: form.stock,
      type: form.type,
      category_name: form.category_name,
      image: form.image || '',
    }

    if (isEdit.value) {
      await adminApi.updateProduct(editId.value, data)
      ElMessage.success('商品更新成功')
    } else {
      await adminApi.createProduct(data)
      ElMessage.success('商品创建成功')
    }

    dialogVisible.value = false
    loadProducts()
  } catch {
    // Error messages handled by interceptor
  } finally {
    submitting.value = false
  }
}

// --- Toggle Active ---
async function toggleActive(row) {
  const action = row.is_active ? '下架' : '上架'
  try {
    await adminApi.toggleProductActive(row.id)
    ElMessage.success(`商品已${action}`)
    loadProducts()
  } catch {
    // Handled by interceptor
  }
}

// --- Delete (soft-delete) ---
function confirmDelete(row) {
  deleteProductId.value = row.id
  deleteProductName.value = row.name
  deleteDialogVisible.value = true
}

async function doDelete() {
  deleting.value = true
  try {
    // Soft delete: set is_active = false
    await adminApi.toggleProductActive(deleteProductId.value)
    ElMessage.success('商品已删除（下架）')
    deleteDialogVisible.value = false
    loadProducts()
  } catch {
    // Handled by interceptor
  } finally {
    deleting.value = false
  }
}

// ============================================================
// Init
// ============================================================
onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.page-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--text-primary);
}

/* KPI card reused from Admin.vue style system */
.kpi-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  border: 1px solid var(--border-color);
  transition: box-shadow .25s ease, border-color .25s ease;
}
.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
  border-color: #d0d5dd;
}

.card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mt-md {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.text-muted {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* Image placeholder */
.image-placeholder {
  width: 60px;
  height: 60px;
  background: var(--bg-page);
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--text-secondary);
}

/* Image upload area */
.image-upload-area {
  width: 100%;
}

.image-mode-toggle {
  margin-bottom: 10px;
}

.image-preview-wrapper {
  position: relative;
  display: inline-block;
}

.image-remove-btn {
  position: absolute;
  top: 12px;
  right: 4px;
}

/* Delete warning */
.delete-warning {
  text-align: center;
  padding: 16px 0;
}
.delete-warning p {
  margin: 8px 0;
  font-size: 14px;
  color: var(--text-primary);
}
.delete-warning .text-muted {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
