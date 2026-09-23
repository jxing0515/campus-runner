<template>
  <div class="page">
    <el-card shadow="never" style="margin-bottom: 14px">
      <div class="filter-bar">
        <span>统计范围</span>
        <el-radio-group v-model="days" @change="load">
          <el-radio-button :value="7">近 7 天</el-radio-button>
          <el-radio-button :value="30">近 30 天</el-radio-button>
          <el-radio-button :value="90">近 90 天</el-radio-button>
        </el-radio-group>
        <span class="grow" />
        <el-button size="small" @click="load">刷新</el-button>
      </div>
      <el-descriptions :column="4" border>
        <el-descriptions-item v-for="c in cards" :key="c.label" :label="c.label">{{ c.value }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="charts">
      <div ref="trendRef" class="chart" />
      <div ref="creditRef" class="chart" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { adminApi } from '../api/request'
import { CREDIT_LEVEL, label } from '../utils/constants'

const days = ref(7)
const overview = ref({})
const cards = computed(() => {
  const o = overview.value || {}
  return [
    { label: '订单总数', value: o.order_count ?? o.total_orders ?? '-' },
    { label: '已完成', value: o.completed_count ?? '-' },
    { label: '取消/异常', value: o.abnormal_count ?? o.cancelled_count ?? '-' },
    { label: '完成率', value: o.complete_rate != null ? `${o.complete_rate}%` : '-' },
    { label: '新增用户', value: o.new_users ?? '-' },
    { label: '新增跑腿员', value: o.new_runners ?? '-' },
    { label: '平台流水', value: o.gmv ?? '-' },
    { label: '平台服务费', value: o.platform_fee ?? '-' },
  ]
})

const trendRef = ref()
const creditRef = ref()
let trendChart
let creditChart

async function load() {
  overview.value = (await adminApi.statsOverview().catch(() => ({}))) || {}
  const [trend, credit] = await Promise.all([
    adminApi.ordersTrend(days.value).catch(() => []),
    adminApi.creditDistribution().catch(() => ({})),
  ])
  const trendRows = trend?.results || trend?.trend || trend || []
  trendChart.setOption({
    grid: { left: 48, right: 24, top: 40, bottom: 32 },
    tooltip: { trigger: 'axis' },
    title: { text: `订单量趋势（近 ${days.value} 天）`, textStyle: { fontSize: 14 } },
    xAxis: { type: 'category', data: trendRows.map((r) => r.date || r.day) },
    yAxis: { type: 'value' },
    series: [
      { name: '订单量', type: 'bar', barMaxWidth: 28, data: trendRows.map((r) => r.count ?? r.total ?? 0) },
      { name: '完成数', type: 'line', smooth: true, data: trendRows.map((r) => r.completed ?? 0) },
    ],
  })
  const d = credit || {}
  const keys = Object.keys(CREDIT_LEVEL).filter((k) => d[k] !== undefined)
  creditChart.setOption({
    tooltip: { trigger: 'item' },
    title: { text: '信用分布', textStyle: { fontSize: 14 } },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['38%', '62%'],
        center: ['50%', '52%'],
        data: (keys.length ? keys.map((k) => [k, d[k]]) : Object.entries(d)).map(([k, v]) => ({
          name: label(CREDIT_LEVEL, k),
          value: v,
        })),
      },
    ],
  })
}

const resize = () => {
  trendChart?.resize()
  creditChart?.resize()
}

onMounted(async () => {
  trendChart = echarts.init(trendRef.value)
  creditChart = echarts.init(creditRef.value)
  window.addEventListener('resize', resize)
  await load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  trendChart?.dispose()
  creditChart?.dispose()
})
</script>
