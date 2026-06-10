<template>
  <div class="admin-page">
    <el-container>
      <el-aside width="220px" class="admin-sidebar">
        <div class="sidebar-brand">
          <strong>ShopMiner</strong>
          <span>管理后台</span>
        </div>
        <el-menu :default-active="activeTab" @select="activeTab = $event">
          <el-menu-item index="dashboard"><el-icon><DataAnalysis /></el-icon>数据看板</el-menu-item>
          <el-menu-item index="rfm"><el-icon><PieChart /></el-icon>客户分群</el-menu-item>
          <el-menu-item index="sales"><el-icon><TrendCharts /></el-icon>销售分析</el-menu-item>
          <el-menu-item index="association"><el-icon><Connection /></el-icon>关联规则</el-menu-item>
          <el-menu-item index="churn"><el-icon><Warning /></el-icon>流失预警</el-menu-item>
          <el-menu-item index="models"><el-icon><Cpu /></el-icon>模型指标</el-menu-item>
          <el-menu-item index="orders"><el-icon><List /></el-icon>订单管理</el-menu-item>
          <el-menu-item index="products"><el-icon><Goods /></el-icon>商品管理</el-menu-item>
          <el-menu-item index="users"><el-icon><User /></el-icon>用户管理</el-menu-item>
        </el-menu>
        <div class="sidebar-footer">
          <div class="compute-time" v-if="lastComputeTime"><el-icon><Clock /></el-icon> {{ lastComputeTime }}</div>
          <el-button type="primary" size="small" :loading="recomputing" @click="triggerRecompute" style="width:100%">重新计算</el-button>
        </div>
      </el-aside>

      <el-main class="admin-main">
        <!-- ============================ DASHBOARD ============================ -->
        <template v-if="activeTab === 'dashboard'">
          <h2 class="page-title">数据看板</h2>
          <el-row :gutter="16" class="stat-cards">
            <el-col :span="dashboardStats.length > 4 ? 4 : 6" v-for="stat in dashboardStats" :key="stat.label">
              <div class="stat-card">
                <div class="stat-value">{{ stat.value }}</div>
                <div class="stat-label">{{ stat.label }}</div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="kpi-card">
                <h3 class="card-title">销售趋势</h3>
                <div ref="dashTrendRef" class="chart-box" style="height:280px"></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="kpi-card">
                <h3 class="card-title">品类销售占比</h3>
                <div ref="dashCategoryRef" class="chart-box" style="height:280px"></div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="16" class="mt-md">
            <el-col :span="12">
              <div class="kpi-card">
                <h3 class="card-title">客户分群概览</h3>
                <div ref="dashRfmRef" class="chart-box" style="height:280px"></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="kpi-card">
                <h3 class="card-title">流失风险分布</h3>
                <div ref="dashChurnRef" class="chart-box" style="height:280px"></div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="16" class="mt-md">
            <el-col :span="24">
              <div class="kpi-card">
                <h3 class="card-title">关键指标仪表盘</h3>
                <div ref="dashGaugeRef" class="chart-box" style="height:220px"></div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="16" class="mt-md">
            <el-col :span="24">
              <div class="kpi-card" style="border: 1px solid #E6A23C">
                <h3 class="card-title" style="color:#E6A23C">系统维护</h3>
                <div style="padding:8px 0">
                  <p style="margin-bottom:12px;color:#909399;font-size:13px">
                    <b>重置账户：</b>恢复管理员/测试账户为默认信息。<br>
                    <b>清空测试数据：</b>仅清理测试产生的订单、购物车、评价和分析结果，UCI原始商品/订单/用户不受影响。<br>
                    <b>导入数据：</b>将 UCI Online Retail 数据集导入系统（如已导入则跳过）。
                  </p>
                  <el-button type="warning" size="small" style="margin-right:8px" @click="resetAccounts" :loading="resetting">重置系统账户</el-button>
                  <el-button type="danger" size="small" style="margin-right:8px" @click="resetAll" :loading="resetting">清空测试数据</el-button>
                  <el-button type="success" size="small" @click="importUciData" :loading="importing">导入 UCI 数据</el-button>
                </div>
              </div>
            </el-col>
          </el-row>
        </template>

        <!-- ============================ RFM ============================ -->
        <template v-if="activeTab === 'rfm'">
          <h2 class="page-title">客户分群 (K-Means + RFM)</h2>
          <div class="kpi-card">
            <div v-if="rfmSegments.length">
              <div ref="rfmChartRef" class="chart-box" style="height:380px"></div>
              <el-table :data="rfmSegments" stripe class="mt-md">
                <el-table-column prop="segment" label="分群" />
                <el-table-column prop="count" label="用户数" />
                <el-table-column prop="avg_recency" label="平均R（最近消费天数）" />
                <el-table-column prop="avg_frequency" label="平均F（消费频率）" />
                <el-table-column prop="avg_monetary" label="平均M（消费金额）" />
              </el-table>
            </div>
            <div v-else class="demo-rfm">
              <div class="demo-rfm-header">
                <el-icon :size="48" color="#409EFF"><PieChart /></el-icon>
                <h3>RFM 分析模型</h3>
                <p>通过 Recency、Frequency、Monetary 三个维度对用户进行分层</p>
              </div>
              <el-row :gutter="16" class="mt-md">
                <el-col :span="8" v-for="demo in rfmDemoData" :key="demo.segment">
                  <div class="demo-card" :style="{ borderLeftColor: demo.color }">
                    <div class="demo-card-name">{{ demo.segment }}</div>
                    <div class="demo-card-desc">{{ demo.desc }}</div>
                    <div class="demo-card-action">{{ demo.action }}</div>
                  </div>
                </el-col>
              </el-row>
              <div ref="rfmDemoChartRef" class="chart-box" style="height:280px;margin-top:20px"></div>
              <div class="empty-state"><p>暂无RFM分群数据</p><p class="text-muted">请先导入数据并点击左侧"重新计算"按钮生成分析结果</p></div>
            </div>
          </div>
        </template>

        <!-- ============================ SALES ============================ -->
        <template v-if="activeTab === 'sales'">
          <h2 class="page-title">销售分析</h2>
          <el-tabs v-model="salesSubTab" type="card" class="sub-tabs">
            <el-tab-pane label="销售趋势" name="trend">
              <div class="kpi-card">
                <h3 class="card-title">销售趋势</h3>
                <div ref="salesTrendChartRef" class="chart-box" style="height:350px"></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="销售预测" name="prediction">
              <el-row :gutter="16" class="mb-md" v-if="predictionMetricsLoaded">
                <el-col :span="6" v-for="card in predictionMetricCards" :key="card.key">
                  <div class="metric-card" :class="`metric-card--${card.tone}`">
                    <div class="metric-card__head">
                      <el-icon class="metric-card__icon"><component :is="card.icon" /></el-icon>
                      <span class="metric-card__title">{{ card.title }}</span>
                    </div>
                    <div class="metric-card__value">
                      <span class="metric-card__number">{{ card.number }}</span>
                      <span v-if="card.unit" class="metric-card__unit">{{ card.unit }}</span>
                    </div>
                    <div class="metric-card__foot">
                      <span class="metric-card__hint">{{ card.hint }}</span>
                    </div>
                  </div>
                </el-col>
              </el-row>
              <div class="kpi-card">
                <h3 class="card-title">销售预测 (LightGBM)</h3>
                <div ref="salesPredChartRef" class="chart-box" style="height:350px"></div>
                <el-table :data="salesPredTableData" stripe class="mt-md" v-if="salesPredTableData.length" size="small">
                  <el-table-column prop="date" label="预测月份" width="120" align="center" />
                  <el-table-column prop="amount" label="预测销售额 (元)" min-width="160" align="right"><template #default="{ row }">{{ fmtMoney(row.amount) }}</template></el-table-column>
                  <el-table-column prop="lower" label="下限 (95%)" min-width="140" align="right"><template #default="{ row }">{{ row.lower ? fmtMoney(row.lower) : '-' }}</template></el-table-column>
                  <el-table-column prop="upper" label="上限 (95%)" min-width="140" align="right"><template #default="{ row }">{{ row.upper ? fmtMoney(row.upper) : '-' }}</template></el-table-column>
                </el-table>
                <div v-else class="empty-state" style="padding:20px">暂无预测数据</div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <!-- ============================ ASSOCIATION ============================ -->
        <template v-if="activeTab === 'association'">
          <h2 class="page-title">关联规则</h2>
          <div class="kpi-card">
            <el-table :data="associationRules" stripe v-loading="loadingAssociation">
              <el-table-column prop="antecedent" label="前件" min-width="120" />
              <el-table-column prop="consequent" label="后件" min-width="120" />
              <el-table-column prop="support" label="支持度" width="100"><template #default="{ row }">{{ (row.support * 100).toFixed(2) }}%</template></el-table-column>
              <el-table-column prop="confidence" label="置信度" width="100"><template #default="{ row }">{{ (row.confidence * 100).toFixed(2) }}%</template></el-table-column>
              <el-table-column prop="lift" label="提升度" width="100"><template #default="{ row }">{{ row.lift.toFixed(2) }}</template></el-table-column>
            </el-table>
            <el-pagination v-if="associationTotal > associationPerPage" v-model:current-page="associationPage" :page-size="associationPerPage" :total="associationTotal" layout="prev,pager,next" class="mt-md" @current-change="loadAssociationRules" />
          </div>
        </template>

        <!-- ============================ CHURN ============================ -->
        <template v-if="activeTab === 'churn'">
          <h2 class="page-title">流失预警</h2>
          <el-row :gutter="16" class="mb-md">
            <el-col :span="8">
              <div class="mini-kpi"><div class="mini-kpi-label">高风险用户</div><div class="mini-kpi-value" style="color:#F56C6C">{{ churnHighRisk }}</div></div>
            </el-col>
            <el-col :span="8">
              <div class="mini-kpi"><div class="mini-kpi-label">中风险用户</div><div class="mini-kpi-value" style="color:#E6A23C">{{ churnMediumRisk }}</div></div>
            </el-col>
            <el-col :span="8">
              <div class="mini-kpi"><div class="mini-kpi-label">已解决</div><div class="mini-kpi-value" style="color:#67C23A">{{ churnResolved }}</div></div>
            </el-col>
          </el-row>
          <div class="kpi-card">
            <div class="card-toolbar">
              <el-checkbox v-model="churnRiskOnly" @change="loadChurnList">仅显示高风险</el-checkbox>
            </div>
            <el-table :data="churnList" stripe v-loading="loadingChurn">
              <el-table-column prop="user_id" label="ID" width="60" />
              <el-table-column prop="user_name" label="用户" width="110" />
              <el-table-column prop="segment" label="RFM分群" width="100" />
              <el-table-column prop="churn_probability" label="流失概率" width="130">
                <template #default="{ row }"><el-progress :percentage="Math.round(row.churn_probability * 100)" :color="churnColor(row.churn_probability)" :stroke-width="14" /></template>
              </el-table-column>
              <el-table-column prop="risk_level" label="风险" width="80">
                <template #default="{ row }"><el-tag :type="row.risk_level==='high'?'danger':row.risk_level==='medium'?'warning':'success'" size="small">{{ {high:'高',medium:'中',low:'低'}[row.risk_level]||row.risk_level }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }"><el-select v-model="row.status" size="small" @change="updateChurnStatus(row)"><el-option label="待处理" value="pending"/><el-option label="已联系" value="contacted"/><el-option label="已解决" value="resolved"/></el-select></template>
              </el-table-column>
              <el-table-column prop="prediction_date" label="预测日期" width="110" />
            </el-table>
            <el-pagination v-if="churnTotal>churnPerPage" v-model:current-page="churnPage" :page-size="churnPerPage" :total="churnTotal" layout="prev,pager,next" class="mt-md" @current-change="loadChurnList" />
          </div>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="kpi-card mt-md"><h3 class="card-title">流失趋势</h3><div ref="churnTrendChartRef" class="chart-box" style="height:280px"></div></div>
            </el-col>
            <el-col :span="12">
              <div class="kpi-card mt-md"><h3 class="card-title">特征重要性</h3><div ref="importanceChartRef" class="chart-box" style="height:280px"></div></div>
            </el-col>
          </el-row>
        </template>

        <!-- ============================ MODELS ============================ -->
        <template v-if="activeTab === 'models'">
          <h2 class="page-title">模型指标</h2>
          <div v-if="modelMetrics && modelGrouped.length">
            <div v-for="group in modelGrouped" :key="group.model" class="kpi-card" style="margin-bottom:16px">
              <div class="model-header" @click="toggleModelExpand(group.model)">
                <h3 class="card-title" style="margin-bottom:0">{{ modelLabel(group.model) }}</h3>
                <div class="model-header-right">
                  <el-tag size="small" type="success">{{ group.keyMetrics.length }}项核心指标</el-tag>
                  <el-tag size="small" type="info" style="margin-left:6px">{{ group.metrics.length }}项总计</el-tag>
                  <el-icon class="expand-icon" :class="{ 'is-expanded': expandedModels[group.model] }"><ArrowRight /></el-icon>
                </div>
              </div>
              <div class="model-key-metrics">
                <el-row :gutter="12">
                  <el-col :span="6" v-for="km in group.keyMetrics" :key="km.metric_name">
                    <div class="model-metric-card">
                      <div class="model-metric-value">{{ formatMetricValueDisplay(km) }}</div>
                      <div class="model-metric-name">{{ formatMetricName(km.metric_name) }}</div>
                    </div>
                  </el-col>
                </el-row>
              </div>

              <!-- ============ 主页面核心业务图 + 详情按钮 ============ -->
              <div v-if="vizModelKey(group.model)" class="model-viz-section">
                <el-row :gutter="16">
                  <el-col :span="18">
                    <div class="viz-chart-title">
                      <el-icon><DataLine /></el-icon>
                      <span>{{ modelCoreChartTitle(group.model) }}</span>
                    </div>
                    <div :id="`core-viz-${vizModelKey(group.model)}`" class="chart-box" style="height:280px"></div>
                  </el-col>
                  <el-col :span="6">
                    <div class="viz-summary-card">
                      <div class="viz-summary-title">业务洞察</div>
                      <div class="viz-summary-text">{{ modelCoreInsight(group.model) }}</div>
                      <div class="viz-action-row">
                        <el-button type="primary" size="default" class="viz-action-btn" @click="openModelDialog(group.model)">
                          <el-icon><View /></el-icon><span>查看可视化详情</span>
                        </el-button>
                      </div>
                      <div class="viz-action-row">
                        <el-button size="default" class="viz-action-btn" @click="loadModelViz(group.model)" :loading="loadingViz[group.model]">
                          <el-icon><Refresh /></el-icon><span>刷新图表数据</span>
                        </el-button>
                      </div>
                    </div>
                  </el-col>
                </el-row>
              </div>

              <el-collapse-transition>
                <div v-show="expandedModels[group.model]" class="model-detail-section">
                  <el-divider content-position="left">全部指标</el-divider>
                  <el-table :data="formatModelTable(group.metrics)" stripe size="small">
                    <el-table-column prop="name" label="指标名称" min-width="160" />
                    <el-table-column prop="displayValue" label="数值" width="140"><template #default="{ row }"><span :class="{ 'metric-key': row.isKey }">{{ row.displayValue }}</span></template></el-table-column>
                    <el-table-column prop="detail" label="说明" min-width="200"><template #default="{ row }">{{ row.detail || '-' }}</template></el-table-column>
                  </el-table>
                </div>
              </el-collapse-transition>
              <div class="model-expand-btn" @click="toggleModelExpand(group.model)">
                <span>{{ expandedModels[group.model] ? '收起详细指标' : '展开全部指标' }}</span>
                <el-icon :class="{ 'is-expanded': expandedModels[group.model] }"><ArrowRight /></el-icon>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">暂无模型指标数据，请先导入数据</div>

          <!-- ============ 详情弹窗：全量技术图表 ============ -->
          <el-dialog
            v-model="dialogVisible"
            :title="dialogTitle"
            width="92%"
            top="3vh"
            :close-on-click-modal="false"
            destroy-on-close
            class="model-viz-dialog"
            @close="disposeDialogCharts"
          >
            <div v-if="dialogLoading" class="dialog-loading">
              <el-icon class="is-loading"><Loading /></el-icon>加载可视化数据中...
            </div>
            <div v-else-if="dialogData" class="dialog-content">
              <div class="dialog-meta">
                <el-tag v-for="(v, k) in filteredDialogMeta" :key="k" size="small" :type="dialogMetaTagType(k)" style="margin-right:6px;margin-bottom:4px">
                  {{ dialogMetaLabel(k) }}: {{ v }}
                </el-tag>
                <span v-if="dialogData.metadata?.version" class="dialog-version-hint">当前版本: {{ dialogData.metadata.version }}</span>
              </div>

              <!-- Phase 3: Clustering Dialog -->
              <template v-if="dialogModelKey === 'phase3'">
                <el-row :gutter="16">
                  <el-col :span="14">
                    <div class="dialog-chart-title">PCA 2D 聚类散点图（1500 抽样）</div>
                    <div ref="p3PcaRef" class="chart-box" style="height:380px"></div>
                  </el-col>
                  <el-col :span="10">
                    <div class="dialog-chart-title">各簇 RFM 画像（规模 / R / F / M）</div>
                    <div ref="p3ProfileRef" class="chart-box" style="height:380px"></div>
                  </el-col>
                </el-row>
                <div class="dialog-chart-title" style="margin-top:16px">各簇业务画像</div>
                <el-table :data="dialogData.cluster_profiles" stripe size="small" class="mt-sm">
                  <el-table-column prop="label" label="簇标签" width="180" />
                  <el-table-column prop="size" label="用户数" width="100" />
                  <el-table-column prop="recency" label="R (天)" width="100" />
                  <el-table-column prop="frequency" label="F (订单)" width="100" />
                  <el-table-column prop="monetary" label="M (元)" width="100" />
                </el-table>
              </template>

              <!-- Phase 4: Churn Dialog -->
              <template v-if="dialogModelKey === 'phase4'">
                <el-row :gutter="16">
                  <el-col :span="12">
                    <div class="dialog-chart-title">ROC 曲线（测试集）</div>
                    <div ref="p4RocRef" class="chart-box" style="height:340px"></div>
                  </el-col>
                  <el-col :span="12">
                    <div class="dialog-chart-title">OOT 滚动窗口 AUC 时序</div>
                    <div ref="p4OotRef" class="chart-box" style="height:340px"></div>
                  </el-col>
                </el-row>
                <div class="dialog-chart-title" style="margin-top:16px">Top 15 特征重要性（XGBoost gain）</div>
                <div ref="p4FeatureRef" class="chart-box" style="height:380px"></div>
              </template>

              <!-- Phase 5: Sales Forecast Dialog -->
              <template v-if="dialogModelKey === 'phase5'">
                <el-row :gutter="16">
                  <el-col :span="16">
                    <div class="dialog-chart-title">实际 vs 预测（最近 8 周测试集）</div>
                    <div ref="p5ActualPredRef" class="chart-box" style="height:340px"></div>
                  </el-col>
                  <el-col :span="8">
                    <div class="dialog-chart-title">残差分布</div>
                    <div ref="p5ResidualRef" class="chart-box" style="height:340px"></div>
                  </el-col>
                </el-row>
                <div class="dialog-chart-title" style="margin-top:16px">月度季节性（所有历史数据）</div>
                <div ref="p5SeasonalRef" class="chart-box" style="height:280px"></div>
              </template>

              <!-- Phase 6: Association Dialog -->
              <template v-if="dialogModelKey === 'phase6'">
                <el-row :gutter="16">
                  <el-col :span="14">
                    <div class="dialog-chart-title">Top 20 规则（按 Lift 排序）</div>
                    <div ref="p6TopRulesRef" class="chart-box" style="height:380px"></div>
                  </el-col>
                  <el-col :span="10">
                    <div class="dialog-chart-title">规则散点：支持度 vs 置信度（颜色=lift）</div>
                    <div ref="p6ScatterRef" class="chart-box" style="height:380px"></div>
                  </el-col>
                </el-row>
                <div class="dialog-chart-title" style="margin-top:16px">各分群规则数与平均 Lift</div>
                <div ref="p6ClusterRef" class="chart-box" style="height:300px"></div>
              </template>
            </div>
            <div v-else class="empty-state">暂无可视化数据，请先"重新计算"生成</div>
          </el-dialog>
        </template>

        <!-- ============================ ORDERS ============================ -->
        <template v-if="activeTab === 'orders'">
          <h2 class="page-title">订单管理</h2>
          <div class="kpi-card">
            <el-table :data="adminOrders" stripe v-loading="loadingOrders">
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column prop="user_name" label="用户" width="120" />
              <el-table-column prop="total_amount" label="金额 (元)" min-width="120" align="right"><template #default="{ row }">{{ fmtMoney(row.total_amount) }}</template></el-table-column>
              <el-table-column prop="status" label="状态" width="100"><template #default="{ row }"><el-tag :type="orderStatusType(row.status)" size="small">{{ orderStatusLabel(row.status) }}</el-tag></template></el-table-column>
              <el-table-column prop="shipping_phone" label="收货电话" width="120" />
              <el-table-column prop="tracking_number" label="运单号" width="140"><template #default="{ row }">{{ row.tracking_number || '-' }}</template></el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="160" />
              <el-table-column label="操作" width="200" fixed="right">
                  <template #default="{ row }">
                  <el-button v-if="row.status==='pending'" type="warning" size="small" @click="payOrder(row.id)">付款</el-button>
                  <el-button v-if="row.status==='paid'" type="primary" size="small" @click="shipOrder(row.id)">发货</el-button>
                  <el-button v-if="row.status==='shipped'" type="success" size="small" @click="deliverOrder(row.id)">送达</el-button>
                  <el-button v-if="['pending','paid'].includes(row.status)" type="danger" size="small" @click="refundOrder(row.id)">退款</el-button>
                  </template>
                </el-table-column>
            </el-table>
            <el-pagination v-if="ordersTotal>ordersPerPage" v-model:current-page="ordersPage" :page-size="ordersPerPage" :total="ordersTotal" layout="prev,pager,next" class="mt-md" @current-change="loadAdminOrders" />
          </div>
        </template>

        <!-- ============================ USERS ============================ -->
        <template v-if="activeTab === 'users'">
          <h2 class="page-title">用户管理</h2>
          <div class="kpi-card">
            <el-table :data="adminUsers" stripe v-loading="loadingUsers">
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column prop="first_name" label="名" width="100" />
              <el-table-column prop="last_name" label="姓" width="100" />
              <el-table-column prop="email" label="邮箱" min-width="180" />
              <el-table-column prop="balance" label="余额 (元)" min-width="120" align="right"><template #default="{ row }">{{ fmtMoney(row.balance) }}</template></el-table-column>
              <el-table-column prop="role" label="角色" width="80"><template #default="{ row }"><el-tag :type="row.role==='admin'?'danger':''" size="small">{{ row.role }}</el-tag></template></el-table-column>
              <el-table-column label="操作" width="160"><template #default="{ row }"><el-button type="primary" size="small" @click="adjustBalance(row)">调整余额</el-button></template></el-table-column>
            </el-table>
            <el-pagination v-if="usersTotal>usersPerPage" v-model:current-page="usersPage" :page-size="usersPerPage" :total="usersTotal" layout="prev,pager,next" class="mt-md" @current-change="loadAdminUsers" />
          </div>
        </template>

        <!-- ============================ PRODUCTS ============================ -->
        <template v-if="activeTab === 'products'">
          <ProductManagement />
        </template>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, markRaw } from 'vue'
import { DataAnalysis, PieChart, TrendCharts, Connection, Warning, Cpu, List, User, Goods, Clock, ArrowRight, DataLine, View, Refresh, Loading } from '@element-plus/icons-vue'
import { adminAnalyticsApi, adminApi } from '../api'
import ProductManagement from '../admin/components/ProductManagement.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

const chartInstances = []

function initChart(domRef) {
  if (!domRef.value) return null
  const dom = domRef.value
  const existing = echarts.getInstanceByDom(dom)
  if (existing) existing.dispose()
  const chart = echarts.init(dom)
  chartInstances.push(chart)
  return chart
}

function disposeChartRefs(refList) {
  refList.forEach(r => {
    if (!r.value) return
    const inst = echarts.getInstanceByDom(r.value)
    if (inst) { inst.dispose(); const i = chartInstances.indexOf(inst); if (i > -1) chartInstances.splice(i, 1) }
  })
}

function handleResize() { chartInstances.forEach(c => { try { c.resize() } catch(e){} }) }

function safeRender(renderFn) {
  nextTick(() => { requestAnimationFrame(() => { renderFn() }) })
}

onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => {
  chartInstances.forEach(c => c.dispose())
  chartInstances.length = 0
  window.removeEventListener('resize', handleResize)
})

const activeTab = ref('dashboard')
const salesSubTab = ref('trend')
const recomputing = ref(false)
const resetting = ref(false)
const importing = ref(false)
const lastComputeTime = ref('')

async function loadLastComputeTime() {
  try { const r = await adminAnalyticsApi.getLastComputeTime(); lastComputeTime.value = r.data.last_compute_time || '未知' } catch {}
}
async function triggerRecompute() {
  recomputing.value = true
  try { await adminAnalyticsApi.recompute(); ElMessage.success('重算已启动'); setTimeout(loadLastComputeTime, 3000) } catch {} finally { recomputing.value = false }
}

async function resetAccounts() {
  try {
    await ElMessageBox.confirm('确认将管理员和测试账户恢复为默认信息？', '重置账户', { confirmButtonText: '确认重置', cancelButtonText: '取消', type: 'warning' })
    resetting.value = true
    await adminApi.resetSystem('accounts')
    ElMessage.success('系统账户已重置为默认信息')
  } catch {} finally { resetting.value = false }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm('确认清空所有测试数据？\n将删除：测试订单、购物车记录、评价、分析数据（RFM/预测/关联规则/流失预警）\n并将管理员和测试账户恢复为默认信息。\nUCI原始商品/订单/用户不受影响。\n此操作不可撤销！', '清空测试数据', { confirmButtonText: '确认清空', cancelButtonText: '取消', type: 'error' })
    resetting.value = true
    await adminApi.resetSystem('all')
    ElMessage.success('已清空测试数据，UCI原始数据不受影响')
    setTimeout(() => location.reload(), 1500)
  } catch {} finally { resetting.value = false }
}

async function importUciData() {
  try {
    await ElMessageBox.confirm('将 UCI Online Retail 数据集导入系统？\n如果已导入过则会跳过。', '导入数据', { confirmButtonText: '确认导入', cancelButtonText: '取消', type: 'info' })
    importing.value = true
    await adminApi.importData()
    ElMessage.success('数据导入已启动，请稍后刷新页面查看')
  } catch {} finally { importing.value = false }
}

// ===================================================================
// DASHBOARD
// ===================================================================
const dashboard = ref(null)
const dashTrendRef = ref(null), dashCategoryRef = ref(null), dashRfmRef = ref(null), dashChurnRef = ref(null)
const dashGaugeRef = ref(null)

const dashboardStats = computed(() => {
  if (!dashboard.value) return []
  const d = dashboard.value
  const stats = [
    { label: '总用户', value: (d.total_users || 0).toLocaleString() },
    { label: '总商品', value: (d.total_products || 0).toLocaleString() },
    { label: '总订单', value: (d.total_orders || 0).toLocaleString() },
    { label: '总销售额', value: '¥' + ((d.total_revenue || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) },
  ]
  // Add new algorithm metrics if available
  if (d.clustering_k) stats.push({ label: '客户分群K', value: d.clustering_k })
  if (d.churn_auc) stats.push({ label: '流失AUC', value: d.churn_auc.toFixed(3) })
  if (d.forecast_smape) stats.push({ label: '预测sMAPE', value: (d.forecast_smape * 100).toFixed(2) + '%' })
  if (d.association_rules_count) stats.push({ label: '关联规则数', value: d.association_rules_count })
  return stats
})

async function loadDashboard() {
  try {
    const res = await adminAnalyticsApi.getDashboard()
    dashboard.value = res.data
    await loadDashboardCharts()
  } catch { dashboard.value = null }
}

async function loadDashboardCharts() {
  try {
    const [trendRes, catRes, rfmRes, churnRes] = await Promise.all([
      adminAnalyticsApi.getSalesTrend(),
      adminAnalyticsApi.getHotProducts({ limit: 50 }),
      adminAnalyticsApi.getRfmSummary(),
      adminAnalyticsApi.getChurnList({ per_page: 15000 }),
    ])
    await nextTick()
    safeRender(() => renderDashTrend(trendRes.data || []))
    safeRender(() => renderDashCategory(catRes.data?.products || []))
    safeRender(() => renderDashRfm(rfmRes.data?.segments || []))
    safeRender(() => renderDashChurn(churnRes.data?.predictions || []))
    safeRender(() => renderDashGauge(dashboard.value))
  } catch {}
}

function renderDashTrend(trend) {
  const chart = initChart(dashTrendRef)
  if (!chart || !trend.length) return
  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
    return v.toFixed(0)
  }
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    grid: { left: 60, right: 15, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: trend.slice(-12).map(t => (t.date || '').slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '销售额 (元)', axisLabel: { formatter: fmtY, fontSize: 10 } },
    animationDuration: 600,
    series: [{ type: 'bar', data: trend.slice(-12).map(t => +(((t.amount || 0) / 100).toFixed(2))), itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] }, animationDelay: idx => idx * 40 }],
  })
}

function renderDashCategory(products) {
  const chart = initChart(dashCategoryRef)
  if (!chart || !products.length) return
  const catMap = {}
  products.forEach(p => { catMap[p.category_name || '其他'] = (catMap[p.category_name || '其他'] || 0) + 1 })
  const data = Object.entries(catMap).sort((a, b) => b[1] - a[1]).slice(0, 8)
  chart.setOption({
    tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: '{b}: {c} ({d}%)' },
    series: [{ type: 'pie', radius: ['42%', '72%'], center: ['50%', '52%'], data: data.map(d => ({ name: d[0], value: d[1] })), label: { fontSize: 10 }, itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 2 }, animationDuration: 600 }],
    color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#36CFC9', '#597EF7', '#9254DE'],
  })
}

function renderDashRfm(segments) {
  const chart = initChart(dashRfmRef)
  if (!chart || !segments.length) return
  chart.setOption({
    tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: '{b}: {c}人 ({d}%)' },
    series: [{ type: 'pie', radius: ['42%', '72%'], center: ['50%', '52%'], data: segments.map(s => ({ name: s.segment, value: s.count })), label: { fontSize: 11 }, animationDuration: 600 }],
    color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399'],
  })
}

function renderDashChurn(predictions) {
  const chart = initChart(dashChurnRef)
  if (!chart || !predictions.length) return
  const bins = { low: 0, medium: 0, high: 0 }
  predictions.forEach(p => {
    const level = p.risk_level || 'low'
    if (level === 'high') bins.high++
    else if (level === 'medium') bins.medium++
    else bins.low++
  })
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    grid: { left: 50, right: 15, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: ['低风险', '中风险', '高风险'] },
    yAxis: { type: 'value', name: '人' },
    animationDuration: 600,
    series: [{ type: 'bar', data: [{ value: bins.low, itemStyle: { color: '#67C23A' } }, { value: bins.medium, itemStyle: { color: '#E6A23C' } }, { value: bins.high, itemStyle: { color: '#F56C6C' } }], label: { show: true, position: 'top', fontSize: 12, fontWeight: 600 } }],
  })
}

function renderDashGauge(d) {
  const chart = initChart(dashGaugeRef)
  if (!chart || !d) return
  const totalUsers = d.total_users || 1
  const orderRate = d.total_orders > 0 ? Math.min((d.paid_orders || 0) / d.total_orders * 100, 100) : 0
  const churnRate = Math.min(((d.churn_risk_count || 0) / totalUsers) * 100, 100)
  const revenuePerUser = ((d.total_revenue || 0) / 100 / totalUsers).toFixed(2)
  chart.setOption({
    series: [
      { type: 'gauge', center: ['16%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: 100, title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '{value}%', offsetCenter: [0, '55%'] }, data: [{ value: +orderRate.toFixed(1), name: '订单完成率' }], axisLine: { lineStyle: { width: 10, color: [[0.5, '#67C23A'], [0.8, '#E6A23C'], [1, '#F56C6C']] } }, animationDuration: 800 },
      { type: 'gauge', center: ['50%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: 100, title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '{value}%', offsetCenter: [0, '55%'] }, data: [{ value: +churnRate.toFixed(1), name: '流失风险率' }], axisLine: { lineStyle: { width: 10, color: [[0.3, '#67C23A'], [0.6, '#E6A23C'], [1, '#F56C6C']] } }, animationDuration: 800 },
      { type: 'gauge', center: ['84%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: Math.max(+revenuePerUser * 2 || 100, 100), title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '¥{value}', offsetCenter: [0, '55%'] }, data: [{ value: +revenuePerUser, name: '人均消费(元)' }], axisLine: { lineStyle: { width: 10, color: [[0.5, '#409EFF'], [0.8, '#66B1FF'], [1, '#36CFC9']] } }, animationDuration: 800 },
    ],
  })
}

// ===================================================================
// RFM
// ===================================================================
const rfmSegments = ref([])
const rfmChartRef = ref(null), rfmDemoChartRef = ref(null)

const rfmDemoData = [
  { segment: '高价值客户', color: '#67C23A', desc: '近期消费多、频率高、金额大', action: '重点维护，提供VIP服务' },
  { segment: '潜力客户', color: '#409EFF', desc: '消费频率或金额有提升空间', action: '推送个性化推荐' },
  { segment: '一般客户', color: '#E6A23C', desc: '消费行为中等水平', action: '保持常规触达' },
  { segment: '流失预警', color: '#F56C6C', desc: '长时间未消费，有流失风险', action: '发送召回优惠' },
  { segment: '低价值客户', color: '#909399', desc: '新注册或消费较少', action: '引导完成首单' },
]

async function loadRfm() {
  try {
    const res = await adminAnalyticsApi.getRfmSummary()
    rfmSegments.value = res.data.segments || []
    await nextTick()
    if (rfmSegments.value.length) { safeRender(() => renderRfmChart()) }
    else { safeRender(() => renderRfmDemoChart()) }
  } catch { rfmSegments.value = [] }
}

function renderRfmChart() {
  const chart = initChart(rfmChartRef)
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: '{b}: {c} ({d}%)' },
    series: [{ type: 'pie', radius: ['35%', '65%'], data: rfmSegments.value.map(s => ({ name: s.segment, value: s.count })), label: { formatter: '{b}\n{d}%' }, animationDuration: 600 }],
    color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399'],
  })
}

function renderRfmDemoChart() {
  const chart = initChart(rfmDemoChartRef)
  if (!chart) return
  const data = [{ name: '高价值客户', value: 15 }, { name: '潜力客户', value: 25 }, { name: '一般客户', value: 30 }, { name: '流失预警', value: 18 }, { name: '低价值客户', value: 12 }]
  const colors = { '高价值客户': '#67C23A', '潜力客户': '#409EFF', '一般客户': '#E6A23C', '流失预警': '#F56C6C', '低价值客户': '#909399' }
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    grid: { left: 90, right: 50, top: 10, bottom: 10 },
    xAxis: { type: 'value', name: '占比 (%)' },
    yAxis: { type: 'category', data: data.map(d => d.name), inverse: true },
    animationDuration: 600,
    series: [{ type: 'bar', data: data.map(d => ({ value: d.value, itemStyle: { color: colors[d.name] } })), label: { show: true, position: 'right', formatter: '{c}%' }, animationDelay: idx => idx * 60 }],
  })
}

function fmtMoney(v) {
  if (v == null || isNaN(v)) return '-'
  // Internal storage is pence (×100); display in yuan
  return '¥' + Number(v / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ===================================================================
// SALES
// ===================================================================
const salesTrendChartRef = ref(null), salesPredChartRef = ref(null)
const salesPredTableData = ref([])
const predictionMetricsLoaded = ref(false)
const predictionMetricCards = ref([])
const salesPredData = ref(null)
const salesTrendData = ref([])

async function loadSales() {
  try {
    const [trendRes, predRes] = await Promise.all([
      adminAnalyticsApi.getSalesTrend(),
      adminAnalyticsApi.getSalesPrediction(),
    ])
    salesTrendData.value = trendRes.data || []
    salesPredData.value = predRes.data || {}
    await nextTick()
    safeRender(() => renderSalesTrendChart(salesTrendData.value))

    const predData = predRes.data || {}
    const preds = predData.predictions || []
    salesPredTableData.value = preds.map(p => ({
      date: p.month || '',
      amount: p.pred_amount || 0,
      lower: p.pred_lower || 0,
      upper: p.pred_upper || 0,
    }))

    try {
      const metRes = await adminAnalyticsApi.getPredictionMetrics()
      const metData = metRes.data || {}

      // 取第一个模型下的 4 个关键指标
      const firstModel = Object.values(metData)[0] || {}
      const bestMae = firstModel.best_mae
      const bestR2 = firstModel.best_r2
      const bestSmape = firstModel.best_smape
      const cvSmape = firstModel.cv_smape_mean

      const cards = []
      if (bestMae) {
        const num = +bestMae.value
        const v = isNaN(num) ? bestMae.value : num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        cards.push({
          key: 'mae', title: '最优 MAE', icon: markRaw(Cpu),
          number: v, unit: '元',
          hint: '平均绝对误差 · 越低越好',
          tone: 'blue',
        })
      }
      if (bestR2) {
        const num = +bestR2.value
        const v = isNaN(num) ? bestR2.value : num.toFixed(4)
        cards.push({
          key: 'r2', title: '最优 R²', icon: markRaw(TrendCharts),
          number: v, unit: '/ 1.0',
          hint: '拟合优度 · 越接近 1 越好',
          tone: 'green',
        })
      }
      if (bestSmape) {
        const num = +bestSmape.value
        cards.push({
          key: 'smape', title: '最优 sMAPE', icon: markRaw(DataLine),
          number: num.toFixed(2) + '%', unit: '',
          hint: '对称平均误差 · 越低越好',
          tone: 'orange',
        })
      }
      if (cvSmape) {
        const num = +cvSmape.value
        const numStd = +(firstModel.cv_smape_std?.value || 0)
        cards.push({
          key: 'cv', title: 'CV sMAPE', icon: markRaw(Warning),
          number: num.toFixed(2) + '%', unit: '± ' + numStd.toFixed(2) + '%',
          hint: '5 折交叉验证 · 越稳定越好',
          tone: num < 5 ? 'green' : num < 10 ? 'orange' : 'red',
        })
      }
      if (cards.length) { predictionMetricCards.value = cards; predictionMetricsLoaded.value = true }
    } catch {}
  } catch {}
}

watch(salesSubTab, (tab) => {
  if (tab === 'prediction' && salesPredData.value) {
    nextTick(() => { safeRender(() => renderSalesPredChart(salesPredData.value)) })
  } else if (tab === 'trend' && salesTrendData.value.length) {
    nextTick(() => { safeRender(() => renderSalesTrendChart(salesTrendData.value)) })
  }
})

function renderSalesTrendChart(trend) {
  const chart = initChart(salesTrendChartRef)
  if (!trend || !trend.length) return
  // Convert Order.total_amount (pence) → yuan (£) for display
  const seriesData = trend.map(t => +(((t.amount || 0) / 100).toFixed(2)))
  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
    return v.toFixed(0)
  }
  const xInterval = trend.length > 18 ? Math.floor(trend.length / 12) : 0
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    legend: { data: ['销售额', '订单数'], bottom: 0 },
    grid: { left: 70, right: 60, top: 25, bottom: 50 },
    xAxis: { type: 'category', data: trend.map(t => t.date), axisLabel: { rotate: 45, fontSize: 10, interval: xInterval } },
    yAxis: [
      { type: 'value', name: '销售额 (元)', axisLabel: { formatter: fmtY, fontSize: 10 } },
      { type: 'value', name: '订单数', axisLabel: { fontSize: 10 } },
    ],
    animationDuration: 600,
    series: [
      { name: '销售额', type: 'bar', data: seriesData, yAxisIndex: 0, itemStyle: { color: '#409EFF' } },
      { name: '订单数', type: 'line', data: trend.map(t => t.count), yAxisIndex: 1, itemStyle: { color: '#67C23A' }, smooth: true },
    ],
  })
}

function renderSalesPredChart(data) {
  const chart = initChart(salesPredChartRef)
  if (!chart) return
  const historical = data.historical || []
  const predictions = data.predictions || []
  const histMonths = historical.map(h => h.month)
  const predMonths = predictions.map(p => p.month)
  // Convert Order/SalesPrediction values (pence ×100 scale) → yuan for display
  const toYuan = (v) => +(((v || 0) / 100).toFixed(2))
  const histVals = historical.map(h => toYuan(h.amount))
  const predVals = predictions.map(p => toYuan(p.pred_amount))
  const upper = predictions.map(p => toYuan(p.pred_upper))
  const lower = predictions.map(p => toYuan(p.pred_lower))
  const H = histVals.length, P = predVals.length
  const histData = predVals.length ? [...histVals, predVals[0], ...new Array(P - 1).fill(null)] : [...histVals]
  const predData = predVals.length ? [...new Array(H).fill(null), ...predVals] : []
  const upperData = [...new Array(H).fill(null), ...upper]
  const lowerData = [...new Array(H).fill(null), ...lower]

  const allCats = [...histMonths, ...predMonths]
  const yMax = Math.max(...histVals, ...predVals, ...upper, 0) * 1.1
  const yMin = 0

  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
    return v.toFixed(0)
  }
  const fmtTooltip = (params) => {
    if (!params || !params.length) return ''
    const date = params[0].axisValue
    let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
    for (const p of params) {
      if (p.value == null) continue
      const seriesName = p.seriesName
      const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      html += `<div style="display:flex;justify-content:space-between;gap:12px"><span>${p.marker} ${seriesName}</span><span style="font-weight:600">¥${val}</span></div>`
    }
    return html
  }

  const xInterval = allCats.length > 18 ? Math.floor(allCats.length / 12) : 0

  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis', formatter: fmtTooltip },
    legend: { data: ['历史', '预测', '95% 置信区间'], bottom: 0, textStyle: { fontSize: 12 } },
    grid: { left: 70, right: 30, top: 25, bottom: 50 },
    xAxis: {
      type: 'category', data: allCats,
      axisLabel: { rotate: 45, fontSize: 10, interval: xInterval },
      axisLine: { lineStyle: { color: '#909399' } },
    },
    yAxis: {
      type: 'value', name: '销售额 (元)', min: yMin, max: yMax,
      axisLabel: { formatter: fmtY, fontSize: 10 },
      splitLine: { lineStyle: { type: 'dashed', color: '#E4E7ED' } },
    },
    animationDuration: 600,
    series: [
      { name: '历史', type: 'line', data: histData, itemStyle: { color: '#409EFF' }, lineStyle: { width: 2 }, smooth: true, connectNulls: false, symbol: 'circle', symbolSize: 5, z: 3 },
      { name: '预测', type: 'line', data: predData, itemStyle: { color: '#E6A23C' }, lineStyle: { type: 'dashed', color: '#E6A23C', width: 2 }, smooth: true, connectNulls: true, symbol: 'diamond', symbolSize: 7, z: 3 },
      { name: '95% 置信区间', type: 'line', data: upperData, lineStyle: { opacity: 0 }, symbol: 'none', stack: 'ci_band', areaStyle: { color: 'rgba(230,162,60,0.15)' }, z: 1 },
      { name: '95% 置信区间', type: 'line', data: lowerData.map((l, i) => l - (upperData[i] || 0)), lineStyle: { opacity: 0 }, symbol: 'none', stack: 'ci_band', z: 2 },
    ],
  })
}

// ===================================================================
// ASSOCIATION
// ===================================================================
const associationRules = ref([])
const associationPage = ref(1), associationTotal = ref(0), associationPerPage = 50
const loadingAssociation = ref(false)

async function loadAssociationRules() {
  loadingAssociation.value = true
  try { const r = await adminAnalyticsApi.getAssociationList({ page: associationPage.value, per_page: associationPerPage }); associationRules.value = r.data.rules || []; associationTotal.value = r.data.total || 0 } catch { associationRules.value = [] }
  finally { loadingAssociation.value = false }
}

// ===================================================================
// CHURN
// ===================================================================
const churnList = ref([])
const churnPage = ref(1), churnTotal = ref(0), churnPerPage = 20
const churnRiskOnly = ref(false), loadingChurn = ref(false)
const churnHighRisk = ref(0), churnMediumRisk = ref(0), churnResolved = ref(0)
const importanceChartRef = ref(null), churnTrendChartRef = ref(null)

function churnColor(p) { return p > 0.7 ? '#F56C6C' : p > 0.4 ? '#E6A23C' : '#67C23A' }

async function loadChurnList() {
  loadingChurn.value = true
  try {
    const r = await adminAnalyticsApi.getChurnList({ page: churnPage.value, per_page: churnPerPage, risk_only: churnRiskOnly.value ? '1' : '0' })
    churnList.value = r.data.predictions || []
    churnTotal.value = r.data.total || 0
    if (r.data.summary) {
      churnHighRisk.value = r.data.summary.high || 0
      churnMediumRisk.value = r.data.summary.medium || 0
      churnResolved.value = r.data.summary.resolved || 0
    }
  } catch { churnList.value = [] }
  finally { loadingChurn.value = false }
}

async function updateChurnStatus(row) {
  try { await adminAnalyticsApi.updateChurnStatus(row.id, row.status); ElMessage.success('状态已更新') } catch {}
}

async function loadChurnImportance() {
  try { const r = await adminAnalyticsApi.getChurnImportance(); const d = r.data || {}; await nextTick(); safeRender(() => renderImportanceChart(d)) } catch {}
}

function renderImportanceChart(data) {
  const chart = initChart(importanceChartRef)
  if (!chart) return
  const features = data.feature_counts || []
  if (!features.length) return
  const sorted = [...features].sort((a, b) => b.count - a.count).slice(0, 12)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
    grid: { left: 100, right: 40, top: 8, bottom: 15 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: sorted.map(s => s.feature), inverse: true, axisLabel: { fontSize: 10 } },
    animationDuration: 600,
    series: [{ type: 'bar', data: sorted.map(s => ({ value: s.count, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#66B1FF' }]) } })), label: { show: true, position: 'right', fontSize: 10 } }],
  })
}

async function loadChurnTrend() {
  try { const r = await adminAnalyticsApi.getChurnTrend(); const d = r.data || []; await nextTick(); safeRender(() => renderChurnTrend(d)) } catch {}
}

function renderChurnTrend(data) {
  const chart = initChart(churnTrendChartRef)
  if (!chart || !data.length) return
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;', formatter: function(params) { const d = data[params[0].dataIndex]; return d.bucket + '<br/>用户数: ' + d.count + '<br/>占比: ' + d.rate + '%' } },
    grid: { left: 55, right: 30, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: data.map(d => d.bucket), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '用户数' },
    animationDuration: 600,
    series: [{
      type: 'bar', data: data.map(d => ({
        value: d.count,
        itemStyle: { color: d.bucket.includes('80') || d.bucket.includes('60') ? '#F56C6C' : d.bucket.includes('40') ? '#E6A23C' : '#67C23A' }
      })),
      label: { show: true, position: 'top', formatter: function(p) { return data[p.dataIndex].rate + '%' }, fontSize: 11 },
      barWidth: '40%',
    }],
  })
}

// ===================================================================
// MODEL METRICS
// ===================================================================
const modelMetrics = ref(null)
const expandedModels = ref({})
const modelVizData = ref({})
const loadingViz = ref({})
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const dialogData = ref(null)
const dialogModelKey = ref('')
const dialogTitle = ref('')

const p3PcaRef = ref(null), p3ProfileRef = ref(null)
const p4RocRef = ref(null), p4OotRef = ref(null), p4FeatureRef = ref(null)
const p5ActualPredRef = ref(null), p5ResidualRef = ref(null), p5SeasonalRef = ref(null)
const p6TopRulesRef = ref(null), p6ScatterRef = ref(null), p6ClusterRef = ref(null)

const modelKeyMap = {
  Clustering: { file: 'phase3', name: '客户分群 (K-Means)', coreTitle: '客户分群规模分布', coreInsight: '按 RFM 行为特征将客户自动分成 4 簇，每簇代表不同生命周期阶段与营销策略' },
  RFM: { file: 'phase3', name: 'RFM 用户分群', coreTitle: '分群规模分布', coreInsight: 'RFM 评分分群' },
  Churn: { file: 'phase4', name: '流失预警 (XGBoost)', coreTitle: 'OOT 滚动窗口 AUC', coreInsight: 'XGBoost 模型在 3 个未来时间窗口上验证 AUC 稳定 0.89-0.93，无时序过拟合' },
  SalesForecast: { file: 'phase5', name: '销售预测 (LightGBM)', coreTitle: '实际 vs 预测（最近 8 周）', coreInsight: 'LightGBM + UK 日历特征，测试 sMAPE 4.86%，季节性高峰 (圣诞) 拟合度佳' },
  Association: { file: 'phase6', name: '关联规则 (Apriori)', coreTitle: 'Top 10 高 Lift 关联规则', coreInsight: 'Apriori 双层次挖掘共 694 条全局规则，Lift 均值 11，最大 17' },
}

function vizModelKey(model) { return modelKeyMap[model]?.file || '' }
function modelCoreChartTitle(model) { return modelKeyMap[model]?.coreTitle || '' }
function modelCoreInsight(model) { return modelKeyMap[model]?.coreInsight || '' }
function dialogMetaLabel(k) {
  const labels = {
    K: '聚类数', silhouette: 'Sil', davies_bouldin: 'DB',
    stability_ari: 'ARI', test_auc: 'Test AUC', oot_mean_auc: 'OOT AUC',
    n_features: '特征数', model_type: '模型', version: '版本',
    test_smape: 'sMAPE', test_mape: 'MAPE', n_global_rules: '全局规则数',
    mean_lift: '平均Lift', n_stockcode_rules: '商品级规则数', n_cluster_rules: '分群规则数',
  }
  return labels[k] || k
}
function dialogMetaTagType(k) {
  if (k === 'version') return 'info'
  if (k.includes('auc') || k === 'silhouette' || k === 'stability_ari') return 'success'
  if (k.includes('smape') || k.includes('mape')) return 'warning'
  if (k.includes('rules')) return 'primary'
  return ''
}
const HIDDEN_META_KEYS = new Set(['version', 'model_type'])
const filteredDialogMeta = computed(() => {
  if (!dialogData.value?.metadata) return {}
  const out = {}
  for (const [k, v] of Object.entries(dialogData.value.metadata)) {
    if (!HIDDEN_META_KEYS.has(k)) out[k] = v
  }
  return out
})

function toggleModelExpand(model) {
  expandedModels.value[model] = !expandedModels.value[model]
}

const modelGrouped = computed(() => {
  if (!modelMetrics.value) return []
  const g = []
  for (const [m, metrics] of Object.entries(modelMetrics.value)) {
    if (Array.isArray(metrics) && metrics.length) {
      g.push({ model: m, metrics, keyMetrics: metrics.filter(met => keyMetrics.has(met.metric_name)) })
    }
  }
  return g
})

const modelLabelMap = { RFM: 'RFM 用户分群模型', Clustering: '客户分群 (K-Means)', Association: '关联规则 (Apriori)', Prophet: '销售预测 (Prophet)', SARIMA: '销售预测 (SARIMA)', LightGBM_Weekly: '销售预测 (LightGBM)', SalesForecast: '销售预测 (LightGBM)', Churn: '流失预警 (Stacking集成)', Sensitivity: '灵敏度分析' }
function modelLabel(m) { return modelLabelMap[m] || m }

const metricLabelMap = {
  silhouette_score: '轮廓系数', silhouette_stability_std: '轮廓系数标准差', total_users: '分析用户数', method: '评分方法',
  recency_mean: '平均R值', frequency_mean: '平均F值', monetary_mean: '平均M值', recency_std: 'R标准差', frequency_std: 'F标准差', monetary_std: 'M标准差',
  total_rules: '规则总数', avg_support: '平均支持度', avg_confidence: '平均置信度', avg_lift: '平均提升度', median_lift: '中位提升度',
  high_lift_ratio: '高提升度比', max_lift: '最大提升度', min_lift: '最小提升度', product_coverage: '品类覆盖率',
  accuracy: '准确率', precision: '精确率', recall: '召回率', f1_score: 'F1 值', auc_roc: 'AUC', optimal_threshold: '最优阈值', positive_ratio: '正样本率',
  train_size: '训练样本数', test_size: '测试样本数', feature_count: '特征数量', smote: 'SMOTE', optuna_trials: 'Optuna搜索', label_rule: '标签规则',
  model_type: '模型类型', train_MAE: '训练MAE', train_RMSE: '训练RMSE', train_MAPE: '训练MAPE', test_MAE: '测试MAE', test_RMSE: '测试RMSE', test_MAPE: '测试MAPE',
  data_months: '数据月数', train_months: '训练月数', seasonality_mode: '季节性模式', note: '备注',
  // New algorithm metrics
  K: '聚类数', outliers_removed: '离群点数', stability_ari: '稳定性ARI',
  test_auc: '测试AUC', test_pr_auc: '测试PR-AUC', test_f1: '测试F1', test_precision: '测试精确率', test_recall: '测试召回率',
  test_brier_skill: 'Brier技能分数', split_method: '划分方式', label_method: '标签方式',
  clv_r2_test: 'CLV R²', clv_mape: 'CLV MAPE', npw_f1_weighted: 'NPW F1', npw_accuracy: 'NPW准确率',
  best_smape: '最优sMAPE', best_mae: '最优MAE', best_r2: '最优R²', cv_smape_mean: 'CV sMAPE均值',
  residual_autocorr: '残差自相关', residual_normality_p: '残差正态性p',
  global_rules_count: '全局规则数', stockcode_rules_count: '商品级规则数', cluster_count: '客群数',
  recommendations_count: '推荐数',
  // v5 新增指标
  biz_threshold: '业务约束阈值', biz_f1: '业务F1', oot_auc_mean: 'OOT AUC均值', oot_windows: 'OOT窗口数',
  calibration_LightGBM_raw_auc: 'LightGBM原始AUC', calibration_LightGBM_raw_brier_skill: 'LightGBM原始Brier',
  'calibration_LightGBM+Platt_auc': 'LightGBM+Platt AUC', 'calibration_LightGBM+Platt_brier_skill': 'LightGBM+Platt Brier',
  'calibration_LightGBM+Isotonic_auc': 'LightGBM+Isotonic AUC', 'calibration_LightGBM+Isotonic_brier_skill': 'LightGBM+Isotonic Brier',
  'calibration_Stacking+Platt_auc': 'Stacking+Platt AUC', 'calibration_Stacking+Platt_brier_skill': 'Stacking+Platt Brier',
}

function formatMetricName(name) {
  return metricLabelMap[name] || name.replace(/^segment_ratio_/, '').replace(/^recency_/, 'R-').replace(/^frequency_/, 'F-').replace(/^monetary_/, 'M-')
}

function formatMetricValueDisplay(m) {
  const v = m.metric_value, n = m.metric_name
  if (typeof v !== 'number') return String(v)
  if (!n.startsWith('feature_importance') && /ratio|accuracy|precision|recall|f1|auc/.test(n)) return (v * 100).toFixed(1) + '%'
  if (/MAE|RMSE/.test(n) || ['monetary_mean', 'monetary_std', 'recency_mean', 'recency_std'].includes(n)) return v.toFixed(1)
  if (/silhouette|MSE|MAPE|smape/.test(n)) return v.toFixed(4)
  if (['total_users', 'total_rules', 'train_size', 'test_size', 'feature_count', 'data_months', 'train_months', 'K', 'outliers_removed', 'global_rules_count', 'stockcode_rules_count', 'cluster_count', 'recommendations_count'].includes(n)) return Math.round(v).toString()
  if (['smote', 'optuna_trials', 'method', 'model_type', 'label_rule', 'seasonality_mode', 'note', 'split_method', 'label_method'].includes(n)) return m.detail || String(v)
  if (/brier/.test(n)) return v.toFixed(3)
  if (/r2|_r2/.test(n)) return v.toFixed(4)
  return v.toFixed(2)
}

const keyMetrics = new Set(['silhouette_score', 'accuracy', 'precision', 'recall', 'f1_score', 'auc_roc', 'avg_lift', 'test_MAE', 'test_RMSE', 'test_MAPE', 'test_auc', 'test_f1', 'test_pr_auc', 'test_brier_skill', 'best_smape', 'best_r2', 'K', 'stability_ari', 'clv_r2_test', 'npw_f1_weighted', 'biz_threshold', 'biz_f1', 'oot_auc_mean'])

function formatModelTable(metrics) {
  return metrics.map(m => ({ name: formatMetricName(m.metric_name), value: m.metric_value, displayValue: formatMetricValueDisplay(m), detail: m.detail || '', isKey: keyMetrics.has(m.metric_name) || m.metric_name.includes('test_') }))
}

async function loadModelMetrics() {
  try {
    const r = await adminAnalyticsApi.getModelMetrics()
    modelMetrics.value = r.data
    // 并行加载 4 个模型的 viz 数据
    const vizModels = Object.keys(modelMetrics.value || {}).filter(m => modelKeyMap[m])
    await Promise.all(vizModels.map(m => loadModelViz(m, false)))
    await nextTick()
    safeRender(() => renderModelCharts())
  } catch { modelMetrics.value = null }
}

async function loadModelViz(model, showLoading = true) {
  const key = modelKeyMap[model]?.file
  if (!key) return
  if (showLoading) loadingViz.value[model] = true
  try {
    const r = await adminAnalyticsApi.getModelViz(key)
    modelVizData.value[key] = r.data
    await nextTick()
    safeRender(() => renderCoreChart(key))
  } catch (e) {
    modelVizData.value[key] = null
  } finally {
    if (showLoading) loadingViz.value[model] = false
  }
}

function renderCoreChart(key) {
  const data = modelVizData.value[key]
  if (!data) return
  const el = document.getElementById(`core-viz-${key}`)
  if (!el) return
  const existing = echarts.getInstanceByDom(el)
  if (existing) existing.dispose()
  const chart = echarts.init(el)
  chartInstances.push(chart)

  if (key === 'phase3') {
    const profiles = data.cluster_profiles || []
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
      legend: { bottom: 0 },
      grid: { left: 55, right: 20, top: 15, bottom: 40 },
      xAxis: { type: 'category', data: profiles.map(p => p.label), axisLabel: { rotate: 20, fontSize: 10 } },
      yAxis: { type: 'value', name: '用户数' },
      series: [{
        type: 'bar', barWidth: '50%',
        data: profiles.map((p, i) => ({
          value: p.size,
          itemStyle: { color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#9254DE', '#36CFC9', '#909399'][i % 7], borderRadius: [6, 6, 0, 0] }
        })),
        label: { show: true, position: 'top', fontSize: 11, fontWeight: 600 },
      }],
    })
  } else if (key === 'phase4') {
    const windows = data.oot_windows || []
    chart.setOption({
      tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
      grid: { left: 50, right: 20, top: 25, bottom: 50 },
      xAxis: { type: 'category', data: windows.map(w => w.window), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', min: 0.7, max: 1.0, name: 'AUC' },
      series: [{
        type: 'line', data: windows.map(w => w.auc),
        itemStyle: { color: '#F56C6C' },
        lineStyle: { color: '#F56C6C', width: 3 },
        symbol: 'circle', symbolSize: 12,
        areaStyle: { color: 'rgba(245,108,108,0.15)' },
        label: { show: true, position: 'top', fontSize: 12, fontWeight: 600, formatter: p => p.value.toFixed(4) },
        markLine: { data: [{ type: 'average', name: '平均', label: { formatter: p => '均值 ' + p.value.toFixed(4) } }], lineStyle: { color: '#909399', type: 'dashed' } },
      }],
    })
  } else if (key === 'phase5') {
    const ap = data.actual_pred || []
    chart.setOption({
      tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
      legend: { data: ['实际销售额', '预测销售额'], bottom: 0 },
      grid: { left: 60, right: 20, top: 15, bottom: 40 },
      xAxis: { type: 'category', data: ap.map(d => d.date), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: '¥' },
      series: [
        { name: '实际销售额', type: 'line', data: ap.map(d => d.actual), itemStyle: { color: '#409EFF' }, smooth: true, symbolSize: 8 },
        { name: '预测销售额', type: 'line', data: ap.map(d => d.predicted), itemStyle: { color: '#E6A23C' }, lineStyle: { type: 'dashed' }, smooth: true, symbolSize: 8 },
      ],
    })
  } else if (key === 'phase6') {
    const rules = (data.top_rules || []).slice(0, 10)
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
      grid: { left: 200, right: 50, top: 10, bottom: 15 },
      xAxis: { type: 'value', name: 'Lift' },
      yAxis: { type: 'category', data: rules.map(r => r.antecedent + ' → ' + r.consequent), inverse: true, axisLabel: { fontSize: 10 } },
      series: [{
        type: 'bar',
        data: rules.map((r, i) => ({
          value: r.lift,
          itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#9254DE' }, { offset: 1, color: '#67C23A' }]) }
        })),
        label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value.toFixed(2) },
        barWidth: '60%',
      }],
    })
  }
}

async function openModelDialog(model) {
  const key = modelKeyMap[model]?.file
  if (!key) return
  dialogModelKey.value = key
  dialogTitle.value = `${modelKeyMap[model]?.name} — 可视化详情`
  dialogVisible.value = true
  if (!modelVizData.value[key]) {
    dialogLoading.value = true
    await loadModelViz(model, false)
    dialogLoading.value = false
  }
  dialogData.value = modelVizData.value[key]
  await nextTick()
  setTimeout(() => renderDialogCharts(), 100)
}

function renderDialogCharts() {
  if (dialogModelKey.value === 'phase3') {
    const data = dialogData.value
    if (!data) return
    const pca = initChart(p3PcaRef)
    if (pca) {
      const clusters = {}
      ;(data.pca_points || []).forEach(p => {
        const c = p.cluster
        if (!clusters[c]) clusters[c] = []
        clusters[c].push([p.x, p.y])
      })
      const colors = ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#9254DE', '#36CFC9', '#909399']
      const profiles = data.cluster_profiles || []
      pca.setOption({
        tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: p => `簇 ${p.seriesName}<br/>PCA1: ${p.data[0].toFixed(2)}<br/>PCA2: ${p.data[1].toFixed(2)}` },
        legend: { bottom: 0, data: Object.keys(clusters).map(c => profiles.find(p => p.cluster === c)?.label || `簇 ${c}`) },
        grid: { left: 50, right: 20, top: 15, bottom: 40 },
        xAxis: { type: 'value', name: 'PCA 1', scale: true },
        yAxis: { type: 'value', name: 'PCA 2', scale: true },
        series: Object.keys(clusters).sort().map((c, i) => ({
          name: profiles.find(p => p.cluster === parseInt(c))?.label || `簇 ${c}`,
          type: 'scatter', data: clusters[c], symbolSize: 5,
          itemStyle: { color: colors[i % colors.length], opacity: 0.6 },
        })),
      })
    }
    const profile = initChart(p3ProfileRef)
    if (profile) {
      const profiles = data.cluster_profiles || []
      profile.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
        legend: { data: ['R (天)', 'F (订单)', 'M (元)'], bottom: 0 },
        grid: { left: 50, right: 50, top: 15, bottom: 40 },
        xAxis: { type: 'category', data: profiles.map(p => p.label), axisLabel: { rotate: 20, fontSize: 10 } },
        yAxis: [
          { type: 'value', name: 'R/F', position: 'left' },
          { type: 'value', name: 'M', position: 'right' },
        ],
        series: [
          { name: 'R (天)', type: 'bar', data: profiles.map(p => p.recency), itemStyle: { color: '#F56C6C' } },
          { name: 'F (订单)', type: 'bar', data: profiles.map(p => p.frequency), itemStyle: { color: '#409EFF' } },
          { name: 'M (元)', type: 'bar', yAxisIndex: 1, data: profiles.map(p => p.monetary), itemStyle: { color: '#67C23A' } },
        ],
      })
    }
  } else if (dialogModelKey.value === 'phase4') {
    const data = dialogData.value
    if (!data) return
    const roc = initChart(p4RocRef)
    if (roc) {
      const rocPts = data.roc_curve || []
      roc.setOption({
        tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
        grid: { left: 55, right: 20, top: 25, bottom: 35 },
        xAxis: { type: 'value', name: 'FPR', min: 0, max: 1 },
        yAxis: { type: 'value', name: 'TPR', min: 0, max: 1 },
        series: [
          { name: 'ROC', type: 'line', data: rocPts.map(p => [p.fpr, p.tpr]), itemStyle: { color: '#F56C6C' }, areaStyle: { color: 'rgba(245,108,108,0.15)' }, smooth: true, symbol: 'none' },
          { name: '随机基线', type: 'line', data: [[0, 0], [1, 1]], lineStyle: { color: '#909399', type: 'dashed' }, symbol: 'none' },
        ],
        title: { text: `AUC = ${(data.metadata?.test_auc || 0).toFixed(4)}`, left: 'center', top: 0, textStyle: { fontSize: 12, color: '#F56C6C', fontWeight: 600 } },
      })
    }
    const oot = initChart(p4OotRef)
    if (oot) {
      const windows = data.oot_windows || []
      oot.setOption({
        tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
        grid: { left: 50, right: 20, top: 25, bottom: 50 },
        xAxis: { type: 'category', data: windows.map(w => w.window), axisLabel: { fontSize: 10 } },
        yAxis: { type: 'value', min: 0.7, max: 1.0, name: 'AUC' },
        series: [{
          type: 'bar', barWidth: '50%',
          data: windows.map(w => ({ value: w.auc, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#F56C6C' }, { offset: 1, color: '#FA9090' }]), borderRadius: [8, 8, 0, 0] } })),
          label: { show: true, position: 'top', fontSize: 12, fontWeight: 600, formatter: p => p.value.toFixed(4) },
        }],
        title: { text: `均值 ${(data.metadata?.oot_mean_auc || 0).toFixed(4)}`, left: 'center', top: 0, textStyle: { fontSize: 12, color: '#F56C6C', fontWeight: 600 } },
      })
    }
    const feat = initChart(p4FeatureRef)
    if (feat) {
      const imps = data.feature_importance || []
      feat.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
        grid: { left: 150, right: 50, top: 10, bottom: 25 },
        xAxis: { type: 'value', name: 'Importance (gain)' },
        yAxis: { type: 'category', data: imps.map(d => d.feature), inverse: true, axisLabel: { fontSize: 11 } },
        series: [{
          type: 'bar',
          data: imps.map(d => ({
            value: d.importance,
            itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#36CFC9' }]) }
          })),
          label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value.toFixed(4) },
          barWidth: '60%',
        }],
      })
    }
  } else if (dialogModelKey.value === 'phase5') {
    const data = dialogData.value
    if (!data) return
    const ap = initChart(p5ActualPredRef)
    if (ap) {
      const arr = data.actual_pred || []
      const map = data.actual_pred || []
      ap.setOption({
        tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
        legend: { data: ['实际', '预测', '误差'], bottom: 0 },
        grid: { left: 60, right: 20, top: 15, bottom: 40 },
        xAxis: { type: 'category', data: arr.map(d => d.date), axisLabel: { fontSize: 10 } },
        yAxis: { type: 'value', name: '¥' },
        series: [
          { name: '实际', type: 'bar', data: arr.map(d => d.actual), itemStyle: { color: '#409EFF' }, barWidth: '30%' },
          { name: '预测', type: 'line', data: arr.map(d => d.predicted), itemStyle: { color: '#E6A23C' }, smooth: true, symbolSize: 10 },
          { name: '误差', type: 'line', data: arr.map(d => d.actual - d.predicted), itemStyle: { color: '#F56C6C' }, lineStyle: { type: 'dotted' }, symbol: 'none' },
        ],
        title: { text: `sMAPE = ${(data.metadata?.test_smape || 0).toFixed(2)}%`, left: 'center', top: 0, textStyle: { fontSize: 12, color: '#E6A23C', fontWeight: 600 } },
      })
    }
    const res = initChart(p5ResidualRef)
    if (res) {
      const hist = data.residual_hist || []
      res.setOption({
        tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
        grid: { left: 50, right: 20, top: 15, bottom: 50 },
        xAxis: { type: 'category', data: hist.map(h => h.bin), axisLabel: { rotate: 30, fontSize: 9 } },
        yAxis: { type: 'value', name: '频次' },
        series: [{
          type: 'bar', barWidth: '80%',
          data: hist.map(h => ({ value: h.count, itemStyle: { color: h.center < 0 ? '#F56C6C' : '#67C23A' } })),
        }],
      })
    }
    const sea = initChart(p5SeasonalRef)
    if (sea) {
      const season = data.seasonality || []
      sea.setOption({
        tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
        grid: { left: 60, right: 20, top: 15, bottom: 25 },
        xAxis: { type: 'category', data: season.map(d => d.month_name) },
        yAxis: { type: 'value', name: '周均销售额 ¥' },
        series: [{
          type: 'bar', barWidth: '50%',
          data: season.map((d, i) => ({
            value: d.avg_revenue,
            itemStyle: { color: ['#67C23A', '#67C23A', '#409EFF', '#409EFF', '#409EFF', '#E6A23C', '#E6A23C', '#E6A23C', '#67C23A', '#67C23A', '#F56C6C', '#F56C6C'][i] }
          })),
          label: { show: true, position: 'top', fontSize: 10, formatter: p => '¥' + (p.value / 1000).toFixed(0) + 'k' },
        }],
      })
    }
  } else if (dialogModelKey.value === 'phase6') {
    const data = dialogData.value
    if (!data) return
    const top = initChart(p6TopRulesRef)
    if (top) {
      const rules = data.top_rules || []
      top.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;', formatter: function(p) { const d = rules[p[0].dataIndex]; return `前件: ${d.antecedent}<br/>后件: ${d.consequent}<br/>Support: ${d.support}%<br/>Confidence: ${d.confidence}%<br/>Lift: ${d.lift}` } },
        grid: { left: 220, right: 50, top: 10, bottom: 25 },
        xAxis: { type: 'value', name: 'Lift' },
        yAxis: { type: 'category', data: rules.map(r => r.antecedent + ' → ' + r.consequent), inverse: true, axisLabel: { fontSize: 10 } },
        series: [{
          type: 'bar',
          data: rules.map(r => ({
            value: r.lift,
            itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#9254DE' }, { offset: 1, color: '#36CFC9' }]) }
          })),
          label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value.toFixed(2) },
          barWidth: '70%',
        }],
      })
    }
    const sc = initChart(p6ScatterRef)
    if (sc) {
      const pts = data.scatter || []
      const lifts = pts.map(p => p.lift || 0)
      const liftMin = lifts.length ? Math.min(...lifts) : 1
      const liftMax = lifts.length ? Math.max(...lifts) : 20
      const supports = pts.map(p => p.support || 0)
      const confidences = pts.map(p => p.confidence || 0)
      const xMax = supports.length ? Math.ceil(Math.max(...supports) * 1.1) : 10
      const yMax = confidences.length ? Math.min(100, Math.ceil(Math.max(...confidences) * 1.1)) : 100
      sc.setOption({
        tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: p => {
          const d = p.data
          return `<b>${d.label || '-'}</b><br/>支持度: ${d.support}%<br/>置信度: ${d.confidence}%<br/>Lift: ${d.lift}`
        } },
        grid: { left: 55, right: 80, top: 25, bottom: 45 },
        xAxis: { type: 'value', name: '支持度 %', min: 0, max: xMax, nameLocation: 'middle', nameGap: 28 },
        yAxis: { type: 'value', name: '置信度 %', min: 0, max: yMax, nameLocation: 'middle', nameGap: 38 },
        visualMap: {
          min: liftMin, max: liftMax, dimension: 'lift', orient: 'vertical', right: 10, top: 'middle',
          text: [`高Lift (${liftMax.toFixed(1)})`, `低Lift (${liftMin.toFixed(1)})`],
          textStyle: { fontSize: 10 },
          itemWidth: 12, itemHeight: 80,
          inRange: { color: ['#67C23A', '#E6A23C', '#F56C6C'] },
        },
        series: [{
          name: '规则', type: 'scatter',
          data: pts.map(p => ({ name: p.label, value: [p.support, p.confidence, p.lift], support: p.support, confidence: p.confidence, lift: p.lift, label: p.label })),
          symbolSize: d => Math.max(6, Math.min(22, (d[2] || 1) * 1.5)),
          itemStyle: { opacity: 0.7 },
        }],
      })
    }
    const cl = initChart(p6ClusterRef)
    if (cl) {
      const cs = data.cluster_summary || []
      cl.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;', formatter: function(p) { const d = cs[p[0].dataIndex]; return `簇 ${d.cluster}<br/>用户: ${d.size}<br/>规则数: ${d.n_rules}<br/>平均Lift: ${d.mean_lift}` } },
        legend: { data: ['规则数', '平均Lift'], bottom: 0 },
        grid: { left: 50, right: 50, top: 15, bottom: 40 },
        xAxis: { type: 'category', data: cs.map(c => `簇 ${c.cluster}`) },
        yAxis: [{ type: 'value', name: '规则数' }, { type: 'value', name: 'Lift', min: 0 }],
        series: [
          { name: '规则数', type: 'bar', data: cs.map(c => c.n_rules), itemStyle: { color: '#409EFF' } },
          { name: '平均Lift', type: 'line', yAxisIndex: 1, data: cs.map(c => c.mean_lift), itemStyle: { color: '#F56C6C' }, smooth: true },
        ],
      })
    }
  }
}

function renderModelCharts() {
  Object.keys(modelVizData.value).forEach(key => renderCoreChart(key))
}

// ===================================================================
// ORDERS
// ===================================================================
const adminOrders = ref([])
const ordersPage = ref(1), ordersTotal = ref(0), ordersPerPage = 15
const loadingOrders = ref(false)

const orderStatusMap = { pending: { label: '待付款', type: 'warning' }, paid: { label: '已付款', type: 'primary' }, shipped: { label: '已发货', type: '' }, delivered: { label: '已送达', type: 'success' }, cancelled: { label: '已取消', type: 'info' }, refunded: { label: '已退款', type: 'danger' } }
function orderStatusLabel(s) { return orderStatusMap[s]?.label || s }
function orderStatusType(s) { return orderStatusMap[s]?.type || 'info' }

async function loadAdminOrders() {
  loadingOrders.value = true
  try { const r = await adminApi.getOrders({ page: ordersPage.value, per_page: ordersPerPage }); adminOrders.value = r.data.orders || []; ordersTotal.value = r.data.total || 0 } catch { adminOrders.value = [] }
  finally { loadingOrders.value = false }
}

async function shipOrder(id) {
  try { const { value: t } = await ElMessageBox.prompt('请输入运单号（可选）', '发货', { confirmButtonText: '确认发货', cancelButtonText: '取消' }); await adminApi.shipOrder(id, t || ''); ElMessage.success('已发货'); loadAdminOrders() } catch {}
}
async function deliverOrder(id) { try { await adminApi.deliverOrder(id); ElMessage.success('已送达'); loadAdminOrders() } catch {} }
async function refundOrder(id) { try { await ElMessageBox.confirm('确认退款？', '退款'); await adminApi.refundOrder(id); ElMessage.success('已退款'); loadAdminOrders() } catch {} }
async function payOrder(id) { try { await ElMessageBox.confirm('确认代客付款？', '付款'); await adminApi.payOrder(id); ElMessage.success('已付款'); loadAdminOrders() } catch {} }

// ===================================================================
// USERS
// ===================================================================
const adminUsers = ref([])
const usersPage = ref(1), usersTotal = ref(0), usersPerPage = 15
const loadingUsers = ref(false)

async function loadAdminUsers() {
  loadingUsers.value = true
  try { const r = await adminApi.getUsers({ page: usersPage.value, per_page: usersPerPage }); adminUsers.value = r.data.users || []; usersTotal.value = r.data.total || 0 } catch { adminUsers.value = [] }
  finally { loadingUsers.value = false }
}

async function adjustBalance(user) {
  try { const { value } = await ElMessageBox.prompt('输入调整金额（正数增加，负数减少，单位：元）', '调整余额', { inputPattern: /^-?\d+(\.\d+)?$/, inputErrorMessage: '请输入有效数字' }); await adminApi.adjustBalance(user.id, Math.round(parseFloat(value) * 100)); ElMessage.success('余额已调整'); loadAdminUsers() } catch {}
}

// ===================================================================
// TAB SWITCHING — fixed: no immediate, use onMounted for initial load
// ===================================================================
const loadedTabs = new Set()

function switchToTab(tab) {
  if (loadedTabs.has(tab)) return
  loadedTabs.add(tab)
  switch (tab) {
    case 'dashboard': loadDashboard(); break
    case 'rfm': loadRfm(); break
    case 'sales': loadSales(); break
    case 'association': loadAssociationRules(); break
    case 'churn': loadChurnList(); loadChurnImportance(); loadChurnTrend(); break
    case 'models': loadModelMetrics(); break
    case 'orders': loadAdminOrders(); break
    case 'products': break  // T5: ProductManagement.vue
    case 'users': loadAdminUsers(); break
  }
}

watch(activeTab, (tab, oldTab) => {
  if (oldTab === 'dashboard') { disposeChartRefs([dashTrendRef, dashCategoryRef, dashRfmRef, dashChurnRef, dashGaugeRef]); loadedTabs.delete('dashboard') }
  else if (oldTab === 'rfm') { disposeChartRefs([rfmChartRef, rfmDemoChartRef]); loadedTabs.delete('rfm') }
  else if (oldTab === 'sales') { disposeChartRefs([salesTrendChartRef, salesPredChartRef]); loadedTabs.delete('sales') }
  else if (oldTab === 'churn') { disposeChartRefs([importanceChartRef, churnTrendChartRef]); loadedTabs.delete('churn') }
  else if (oldTab === 'models') {
    ['model-rfm-chart', 'model-churn-chart'].forEach(id => {
      const el = document.getElementById(id)
      if (el) { const inst = echarts.getInstanceByDom(el); if (inst) inst.dispose() }
    })
    ['phase3', 'phase4', 'phase5', 'phase6'].forEach(k => {
      const el = document.getElementById(`core-viz-${k}`)
      if (el) { const inst = echarts.getInstanceByDom(el); if (inst) inst.dispose() }
    })
    disposeDialogCharts()
    loadedTabs.delete('models')
  }
  switchToTab(tab)
})

function disposeDialogCharts() {
  disposeChartRefs([p3PcaRef, p3ProfileRef, p4RocRef, p4OotRef, p4FeatureRef, p5ActualPredRef, p5ResidualRef, p5SeasonalRef, p6TopRulesRef, p6ScatterRef, p6ClusterRef])
}

onMounted(() => {
  loadLastComputeTime()
  switchToTab('dashboard')
})
</script>

<style scoped>
.admin-page { margin: -20px; }
.admin-sidebar { background: var(--bg-card); border-right: 1px solid var(--border-color); min-height: calc(100vh - 60px); display: flex; flex-direction: column; }
.sidebar-brand { padding: 20px; border-bottom: 1px solid var(--border-color); text-align: center; }
.sidebar-brand strong { display: block; font-size: 18px; color: var(--color-primary); }
.sidebar-brand span { font-size: 12px; color: var(--text-secondary); }
.sidebar-footer { margin-top: auto; padding: 16px; border-top: 1px solid var(--border-color); }
.compute-time { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; display: flex; align-items: center; gap: 4px; }
.admin-main { padding: 24px; background: var(--bg-page); min-height: calc(100vh - 60px); }

/* Bento Box card */
.kpi-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  border: 1px solid var(--border-color);
  transition: box-shadow .25s ease, border-color .25s ease;
}
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); border-color: #d0d5dd; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); letter-spacing: .01em; }
.card-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

.stat-cards { margin-bottom: 16px; }
.stat-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 22px 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  border: 1px solid var(--border-color);
  transition: box-shadow .25s ease, transform .2s ease;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); transform: translateY(-2px); }
.stat-value { font-size: 26px; font-weight: 700; color: var(--color-primary); letter-spacing: -.01em; }
.stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 6px; text-transform: uppercase; letter-spacing: .05em; }

.mini-kpi {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  border: 1px solid var(--border-color);
}
.mini-kpi-label { font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; letter-spacing: .03em; }
.mini-kpi-value { font-size: 24px; font-weight: 700; }

/* A. 语义化分级 KPI 卡片 */
.metric-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--border-color);
  height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: box-shadow .2s, transform .2s;
  overflow: hidden;
}
.metric-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.08); transform: translateY(-1px); }
.metric-card--blue { border-left-color: #409EFF; }
.metric-card--green { border-left-color: #67C23A; }
.metric-card--orange { border-left-color: #E6A23C; }
.metric-card--red { border-left-color: #F56C6C; }
.metric-card__head { display: flex; align-items: center; gap: 6px; color: var(--text-secondary); }
.metric-card--blue .metric-card__head .metric-card__icon { color: #409EFF; }
.metric-card--green .metric-card__head .metric-card__icon { color: #67C23A; }
.metric-card--orange .metric-card__head .metric-card__icon { color: #E6A23C; }
.metric-card--red .metric-card__head .metric-card__icon { color: #F56C6C; }
.metric-card__icon { font-size: 16px; }
.metric-card__title { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-card__value { display: flex; align-items: baseline; gap: 4px; }
.metric-card__number {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -.01em;
  color: var(--text-primary);
}
.metric-card__unit { font-size: 12px; color: var(--text-secondary); font-weight: 400; }
.metric-card__foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.metric-card__hint { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.metric-key { color: var(--color-primary); font-weight: 600; }

.chart-box { width: 100%; position: relative; z-index: 1; }

.mt-md { margin-top: 16px; }
.mb-md { margin-bottom: 16px; }
.sub-tabs { margin-bottom: 16px; }

.demo-rfm { text-align: center; }
.demo-rfm-header { padding: 20px; }
.demo-rfm-header h3 { font-size: 18px; margin: 12px 0 8px; }
.demo-rfm-header p { color: var(--text-secondary); font-size: 13px; max-width: 500px; margin: 0 auto; }
.demo-card {
  background: var(--bg-page);
  border-radius: 10px;
  padding: 16px;
  border-left: 4px solid;
  text-align: left;
  margin-bottom: 12px;
  min-height: 100px;
  border: 1px solid var(--border-color);
  transition: box-shadow .2s ease;
}
.demo-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.demo-card-name { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.demo-card-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.demo-card-action { font-size: 12px; color: var(--color-primary); font-weight: 500; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); font-size: 16px; }
.text-muted { color: var(--text-secondary); font-size: 13px; }

/* Model metrics */
.model-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 4px 0; position: relative; z-index: 10; }
.model-header:hover { opacity: 0.85; }
.model-header-right { display: flex; align-items: center; gap: 0; }
.expand-icon { transition: transform .25s ease; margin-left: 8px; font-size: 14px; color: var(--text-secondary); }
.expand-icon.is-expanded { transform: rotate(90deg); }
.model-key-metrics { margin-top: 16px; }
.model-metric-card {
  background: var(--bg-page);
  border-radius: 10px;
  padding: 14px 12px;
  text-align: center;
  border: 1px solid var(--border-color);
  transition: box-shadow .2s ease;
}
.model-metric-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.model-metric-value { font-size: 20px; font-weight: 700; color: var(--color-primary); }
.model-metric-name { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }
.model-detail-section { margin-top: 12px; }
.model-expand-btn {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  margin-top: 12px; padding: 8px 0; cursor: pointer;
  color: var(--color-primary); font-size: 13px; font-weight: 500;
  border-top: 1px dashed var(--border-color);
  transition: background .2s ease;
}
.model-expand-btn:hover { background: var(--bg-page); }
.model-expand-btn .expand-icon { font-size: 12px; }

/* Model viz section */
.model-viz-section { margin-top: 20px; padding-top: 20px; border-top: 1px dashed var(--border-color); }
.viz-chart-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
.viz-chart-title .el-icon { color: var(--color-primary); }
.viz-summary-card { background: var(--bg-page); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; height: 100%; display: flex; flex-direction: column; }
.viz-summary-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.viz-summary-text { font-size: 12px; color: var(--text-secondary); line-height: 1.7; flex: 1; }
.viz-action-row { display: flex; justify-content: center; margin-top: 10px; }
.viz-action-row:first-of-type { margin-top: 12px; }
.viz-action-row .viz-action-btn { display: inline-flex; align-items: center; justify-content: center; gap: 4px; min-width: 0; }
.viz-action-row .viz-action-btn .el-icon { margin-right: 2px; }
.viz-action-row .viz-action-btn span { white-space: nowrap; }

/* Constrain chart z-index so tooltip never covers model-header (see .chart-box above) */

.dialog-content { padding: 0 4px; }
.dialog-loading { text-align: center; padding: 60px 0; color: var(--text-secondary); font-size: 14px; }
.dialog-loading .el-icon { margin-right: 8px; }
.dialog-meta { padding: 8px 0 16px; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 0; }
.dialog-version-hint { font-size: 11px; color: var(--text-secondary); margin-left: auto; padding: 2px 8px; background: var(--bg-page); border-radius: 4px; }
.dialog-chart-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; padding-left: 8px; border-left: 3px solid var(--color-primary); }
.mt-sm { margin-top: 8px; }

/* Dialog header padding for breathing room around X close button */
.model-viz-dialog .el-dialog__header { padding: 20px 24px 16px; }
.model-viz-dialog .el-dialog__title { font-size: 16px; font-weight: 600; }
.model-viz-dialog .el-dialog__headerbtn { top: 18px; right: 20px; width: 32px; height: 32px; }
.model-viz-dialog .el-dialog__headerbtn .el-dialog__close { font-size: 18px; }
.model-viz-dialog .el-dialog__body { padding: 12px 24px 24px; }
</style>
