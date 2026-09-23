<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="订单状态" clearable style="width: 160px" @change="reload">
          <el-option v-for="o in statusOpts" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-checkbox v-model="abnormal" border @change="onAbnormal">仅看异常单</el-checkbox>
        <el-input v-model="query.order_no" placeholder="订单号" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="detail">
              <p><b>状态日志</b></p>
              <el-timeline v-if="(row.logs || row.status_logs || []).length">
                <el-timeline-item
                  v-for="(l, i) in row.logs || row.status_logs"
                  :key="i"
                  :timestamp="fmtDate(l.created_at || l.time)"
                >
                  {{ label(ORDER_STATUS, l.to_status || l.status) }} · {{ l.remark || l.operator || '' }}
                </el-timeline-item>
              </el-timeline>
              <p v-else class="muted">暂无日志（点击「详情」按需加载）</p>
              <p class="muted">
                描述：{{ row.description || '-' }}；取件地：{{ row.pickup_address || '-' }}；送达地：{{ row.delivery_address || '-' }}
              </p>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column label="学生" min-width="100">
          <template #default="{ row }">{{ row.student_name || row.student?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="跑腿员" min-width="100">
          <template #default="{ row }">{{ row.runner_name || row.runner?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="跑腿费" width="100">
          <template #default="{ row }">{{ fmtMoney(row.runner_fee) }}</template>
        </el-table-column>
        <el-table-column label="物品费" width="100">
          <template #default="{ row }">{{ fmtMoney(row.item_fee_actual ?? row.item_fee_estimate) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="tag(ORDER_STATUS, row.status)">{{ label(ORDER_STATUS, row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="异常" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.abnormal || row.status === 'abnormal'" type="danger">异常</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDetail(row)">详情</el-button>
            <el-button link type="danger" @click="openResolve(row)">人工处理</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page.page"
          v-model:page-size="page.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="load"
          @size-change="reload"
        />
      </div>
    </el-card>

    <el-dialog v-model="resolveVisible" title="异常单人工处理" width="440px">
      <el-form :model="resolveForm" label-width="90px">
        <el-form-item label="订单号">{{ resolveForm.order_no }}</el-form-item>
        <el-form-item label="处理动作">
          <el-radio-group v-model="resolveForm.action">
            <el-radio value="complete">强制完成（触发结算）</el-radio>
            <el-radio value="cancel">取消订单（退款）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" required>
          <el-input v-model="resolveForm.remark" type="textarea" :rows="3" placeholder="必填，将写入操作日志" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveVisible = false">取消</el-button>
        <el-button type="danger" :disabled="!resolveForm.remark" @click="submitResolve">确认处理</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="订单详情" size="520px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ label(ORDER_STATUS, detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ detail.description }}</el-descriptions-item>
        <el-descriptions-item label="取件地">{{ detail.pickup_address }}</el-descriptions-item>
        <el-descriptions-item label="送达地">{{ detail.delivery_address }}</el-descriptions-item>
        <el-descriptions-item label="跑腿费">{{ fmtMoney(detail.runner_fee) }}</el-descriptions-item>
      </el-descriptions>
      <el-timeline v-if="detail" style="margin-top: 16px">
        <el-timeline-item
          v-for="(l, i) in detail.logs || detail.status_logs || []"
          :key="i"
          :timestamp="fmtDate(l.created_at || l.time)"
        >
          {{ label(ORDER_STATUS, l.to_status || l.status) }} · {{ l.remark || '' }}
        </el-timeline-item>
      </el-timeline>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { ORDER_STATUS, label, tag } from '../utils/constants'
import { fmtDate, fmtMoney } from '../utils/format'

const statusOpts = computed(() => Object.entries(ORDER_STATUS).map(([value, it]) => ({ value, label: it[0] })))
const query = reactive({ status: '', abnormal: '', order_no: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.orders, query)

const abnormal = ref(false)
const resolveVisible = ref(false)
const resolveForm = reactive({ order_no: '', action: 'complete', remark: '' })
const detailVisible = ref(false)
const detail = ref(null)

function onAbnormal(v) {
  query.abnormal = v ? 1 : ''
  reload()
}
function reset() {
  query.status = ''
  query.order_no = ''
  abnormal.value = false
  query.abnormal = ''
  reload()
}
function openResolve(row) {
  Object.assign(resolveForm, { order_no: row.order_no, action: 'complete', remark: '' })
  resolveVisible.value = true
}
async function submitResolve() {
  await adminApi.resolveOrder(resolveForm.order_no, { action: resolveForm.action, remark: resolveForm.remark })
  ElMessage.success('已处理')
  resolveVisible.value = false
  load()
}
async function showDetail(row) {
  detail.value = await adminApi.order(row.order_no).catch(() => row)
  detailVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.detail { padding: 6px 20px; }
</style>
