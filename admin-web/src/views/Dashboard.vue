<template>
  <div class="page">
    <div class="stat-grid">
      <el-card v-for="c in cards" :key="c.label" shadow="never">
        <div class="label">{{ c.label }}</div>
        <div class="value">{{ c.value }}</div>
      </el-card>
    </div>

    <el-card shadow="never" class="charts">
      <div ref="trendRef" class="chart" />
      <div ref="creditRef" class="chart" />
      <div ref="flowRef" class="chart" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { adminApi } from '../api/request'
import { CREDIT_LEVEL, FUND_FLOW_TYPE, label } from '../utils/constants'

const overview = ref({})

const cards = computed(() => {
  const o = overview.value.order || overview.value.orders || overview.value
  return [
    { label: '用户总数', value: overview.value.user_count ?? o.user_count ?? '-' },
    { label: '跑腿员数', value: overview.value.runner_count ?? o.runner_count ?? '-' },
    { label: '订单总数', value: overview.value.order_count ?? o.total ?? '-' },
    { label: '今日订单', value: overview.value.today_orders ?? o.today ?? '-' },
    { label: '完成率', value: overview.value.complete_rate ? `${overview.value.complete_rate}%` : '-' },
    { label: '平台流水', value: overview.value.gmv ?? overview.value.total_amount ?? '-' },
    { label: '托管中', value: overview.value.escrow ?? o.escrow_amount ?? '-' },
    { label: '待审核认证', value: overview.value.pending_certifications ?? '-' },
    { label: '待审核提现', value: overview.value.pending_withdrawals ?? '-' },
    { label: '待处理异常单', value: overview.value.abnormal_orders ?? '-' },
  ]
})

const trendRef = ref()
const creditRef = ref()
const flowRef = ref()
let charts = []

const base = () => ({ grid: { left: 48, right: 24, top: 48, bottom: 32 }, tooltip: { trigger: 'axis' } })

function renderTrend(rows = []) {
  const days = rows.map((r) => r.date || r.day)
  charts[0].setOption({
    ...base(),
    title: { text: '订单量趋势 / 完成率', textStyle: { fontSize: 14 } },
    legend: { top: 24, data: ['订单量', '完成率'] },
    xAxis: { type: 'category', data: days },
    yAxis: [
      { type: 'value', name: '单' },
      { type: 'value', name: '%', max: 100, min: 0 },
    ],
    series: [
      { name: '订单量', type: 'line', smooth: true, areaStyle: {}, data: rows.map((r) => r.count ?? r.total ?? 0) },
      {
        name: '完成率',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: rows.map((r) => r.complete_rate ?? 0),
      },
    ],
  })
}

function renderCredit(d = {}) {
  const keys = Object.keys(CREDIT_LEVEL).filter((k) => d[k] !== undefined)
  const data = keys.length
    ? keys.map((k) => ({ name: label(CREDIT_LEVEL, k), value: d[k] }))
    : Object.entries(d).map(([name, value]) => ({ name: label(CREDIT_LEVEL, name), value }))
  charts[1].setOption({
    title: { text: '信用分布', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['38%', '62%'], center: ['50%', '52%'], data }],
  })
}

function renderFlow(d = {}) {
  const src = d.stats || d.flows || d.items || []
  const rows = Array.isArray(src) ? src : Object.entries(src).map(([k, v]) => ({ type: k, amount: v }))
  charts[2].setOption({
    ...base(),
    title: { text: '资金流水（按类型）', textStyle: { fontSize: 14 } },
    xAxis: { type: 'category', data: rows.map((r) => label(FUND_FLOW_TYPE, r.type)) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '金额',
        type: 'bar',
        barMaxWidth: 36,
        data: rows.map((r) => r.amount ?? r.total ?? r.value ?? 0),
      },
    ],
  })
}

async function load() {
  overview.value = (await adminApi.statsOverview()) || {}
  const [trend, credit] = await Promise.all([
    adminApi.ordersTrend(7).catch(() => []),
    adminApi.creditDistribution().catch(() => ({})),
  ])
  renderTrend(trend?.results || trend?.trend || trend || [])
  renderCredit(credit || {})
  renderFlow(overview.value.fund_flows || {})
}

const resize = () => charts.forEach((c) => c.resize())

onMounted(async () => {
  charts = [echarts.init(trendRef.value), echarts.init(creditRef.value), echarts.init(flowRef.value)]
  window.addEventListener('resize', resize)
  await load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})
</script>
