<script setup>
import { computed, onMounted, ref } from 'vue'
import CafmNumberCard from '@/components/cafm/CafmNumberCard.vue'
import CafmDonutChart from '@/components/cafm/CafmDonutChart.vue'
import CafmBarChart from '@/components/cafm/CafmBarChart.vue'
import CafmCategoryFunnel from '@/components/cafm/CafmCategoryFunnel.vue'
import CafmSeriesChart from '@/components/cafm/CafmSeriesChart.vue'
import CafmActualForecastChart from '@/components/cafm/CafmActualForecastChart.vue'
import CafmMaintenanceCostChart from '@/components/cafm/CafmMaintenanceCostChart.vue'
import CafmPreventiveCalendar from '@/components/cafm/CafmPreventiveCalendar.vue'

const views={facility:{label:'Facility Management',method:'get_facility_management_analytics'},utility:{label:'Utility Consumption',method:'get_utility_consumption_analytics'},sla:{label:'SLA Performance',method:'get_sla_performance_analytics'}}
const selected=ref(new URLSearchParams(location.search).get('view')||'facility')
if(!views[selected.value])selected.value='facility'
const COLORS={
  blue:'#4463F0',green:'#29CD42',amber:'#F59E0B',red:'#E53935',softRed:'#cc6a6a',
  cyan:'#22B8CF',orange:'#E65100',mediumBlue:'#3B82F6',lowGreen:'#22C55E',
  critical:'#DC2626',gray:'#64748B',gold:'#ffc300',
}
const UTILITY_COLORS=['#2E86DE','#22B8CF','#F59E0B','#E65100','#64748B']
const facilityCardColors=['#4463F0','#4463F0','#cc6a6a','#F59E0B']
const utilityCardColors=['#2E86DE','#F59E0B','#E53935','#F59E0B','#35B779','#2E86DE','#22B8CF','#F59E0B','#E65100']
const slaCardColors=['#35B779','#F59E0B','#E53935','#2E86DE']
function paletteFor(rows,map){return (rows||[]).map(row=>map[String(row.label||'').toLowerCase()]||COLORS.gray)}
const priorityMap={critical:COLORS.critical,high:COLORS.amber,medium:COLORS.mediumBlue,low:COLORS.lowGreen}
const statusMap={draft:'#94A3B8',assigned:'#3B82F6','in progress':'#F59E0B',pending:'#E65100',resolved:'#29CD42',closed:'#35B779',cancelled:'#64748B'}
const slaMap={'on track':'#35B779','response breached':'#F59E0B','resolution breached':'#E53935',met:'#2E86DE'}
const loading=ref(true),error=ref(''),data=ref({})
const title=computed(()=>views[selected.value].label+' Dashboard')
const priorityOrder=['critical','high','medium','low']
const orderedPriorities=computed(()=>[...(data.value.work_orders_by_priority||[])].sort((left,right)=>{
  const leftIndex=priorityOrder.indexOf(String(left.label||'').toLowerCase())
  const rightIndex=priorityOrder.indexOf(String(right.label||'').toLowerCase())
  return (leftIndex<0?priorityOrder.length:leftIndex)-(rightIndex<0?priorityOrder.length:rightIndex)
}))

async function loadDashboard(){loading.value=true;error.value='';try{const response=await fetch('/api/method/cafm.api.'+views[selected.value].method,{credentials:'same-origin',headers:{Accept:'application/json'}});const payload=await response.json();if(!response.ok||payload.exc)throw new Error(payload.exception||'Unable to load dashboard');data.value=payload.message}catch(exception){error.value=exception.message||'Unable to load dashboard'}finally{loading.value=false}}
function selectView(view){selected.value=view;history.replaceState({},'',view==='facility'?'/dashboard':'/dashboard?view='+view);loadDashboard()}
function pairs(source){const labels=source?.labels||[],values=source?.datasets?.[0]?.values||[];return labels.map((label,index)=>({label,value:values[index]||0}))}
onMounted(loadDashboard)
</script>
<template>
<main class="dashboard">
<nav class="tabs" aria-label="Dashboard views"><button v-for="(view,key) in views" :key="key" :class="{active:selected===key}" @click="selectView(key)">{{view.label}}</button></nav>
<header class="dashboard-header"><div><p>CAFM ANALYTICS</p><h1>{{title}}</h1><span>Live operational data from Frappe</span></div><button type="button" class="refresh" @click="loadDashboard">Refresh</button></header>
<div v-if="loading" class="state">Loading dashboard data...</div>
<div v-else-if="error" class="state error"><strong>Dashboard could not load.</strong><span>{{error}}</span><a href="/login?redirect-to=/dashboard">Sign in again</a></div>
<template v-else-if="selected==='facility'">
<section class="kpis"><CafmNumberCard v-for="(stat,index) in data.stats" :key="stat.label" :title="stat.label" :value="stat.value" :color="facilityCardColors[index]" /></section>
<section class="chart-grid"><CafmDonutChart :data="orderedPriorities" :color-map="priorityMap" ordered-legend variant="half" show-inline-labels title="Work orders by priority" subtitle="Current work-order distribution" /><CafmDonutChart :data="data.work_orders_by_status" :palette="paletteFor(data.work_orders_by_status,statusMap)" title="Work orders by status" subtitle="Current lifecycle position" center-label="work orders" /><CafmCategoryFunnel :data="data.work_orders_by_category" /><CafmBarChart :data="data.asset_downtime" :palette="[COLORS.blue,COLORS.cyan,COLORS.amber,COLORS.green,'#8B5CF6',COLORS.orange,COLORS.red,COLORS.gray]" multi-color title="Asset downtime" subtitle="Recorded downtime by asset" unit="Hours" /><CafmBarChart :data="data.recurring_asset_failures" :palette="[COLORS.red,COLORS.amber,COLORS.mediumBlue,COLORS.green,'#8B5CF6',COLORS.cyan,COLORS.orange,COLORS.gray]" multi-color title="Top recurring asset failures" subtitle="Maintenance-history records by asset" horizontal /><CafmPreventiveCalendar :data="data.preventive_maintenance_calendar" /><CafmMaintenanceCostChart class="wide" :data="data.maintenance_cost_by_site" /></section>
</template>
<template v-else-if="selected==='utility'">
<section class="kpis utility-cards"><CafmNumberCard v-for="(card,index) in data.cards" :key="card.label" :title="card.label" :value="card.value" :target="card.target" :compact="card.compact" :trend="card.trend" :trend-type="card.trend_type" :selectable-comparison="card.selectable_comparison" :color="utilityCardColors[index]" /></section>
<section class="chart-grid utility-grid"><CafmSeriesChart class="wide" :source="data.monthly_cost" :palette="UTILITY_COLORS" title="Monthly utility cost" subtitle="Cost by utility type" kind="bar" unit="Cost" /><CafmActualForecastChart class="wide" :series="data.usage_forecast" :colors="UTILITY_COLORS" title="Actual vs Forecast Utility Consumption" subtitle="Recorded monthly consumption compared with the rolling forecast" /></section>
</template>
<template v-else>
<section class="kpis"><CafmNumberCard v-for="(card,index) in data.cards" :key="card.label" :title="card.label" :value="card.value" :color="slaCardColors[index]" /></section>
<section class="chart-grid single"><CafmDonutChart :data="pairs(data.status_breakdown)" :color-map="slaMap" ordered-legend variant="half" show-inline-labels title="Work orders by SLA status" subtitle="Current SLA performance" /></section>
</template>
</main>
</template>
<style scoped>
.dashboard{min-height:100vh;padding:24px 28px 40px;background:#f4f8fb;color:#173650}.tabs{max-width:1440px;margin:0 auto 20px;display:flex;gap:8px;padding:6px;border:1px solid #d5e3ec;border-radius:12px;background:#fff;width:max-content}.tabs button{border:0;border-radius:8px;background:transparent;color:#547187;padding:9px 15px;font-weight:700;cursor:pointer}.tabs button.active{background:#0f6da8;color:#fff}.dashboard-header{max-width:1440px;margin:0 auto 22px;display:flex;align-items:center;justify-content:space-between;gap:20px}.dashboard-header p{margin:0;color:#487391;font-size:11px;font-weight:800;letter-spacing:.08em}.dashboard-header h1{margin:6px 0;font-size:clamp(26px,4vw,38px)}.dashboard-header span{color:#6e8496}.refresh{border:1px solid #87b9dc;border-radius:10px;background:#0f6da8;color:#fff;padding:10px 18px;font-weight:700;cursor:pointer}.refresh:hover{background:#095b90}.state{max-width:1440px;margin:80px auto;padding:28px;border:1px solid #dce7ee;border-radius:14px;background:#fff}.state.error{display:grid;gap:8px;color:#9f2d2d}.kpis{max-width:1440px;margin:0 auto 16px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.utility-cards{grid-template-columns:repeat(4,minmax(0,1fr))}.chart-grid{max-width:1440px;margin:0 auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.chart-grid>:last-child,.chart-grid .wide{grid-column:1/-1}.chart-grid.single{grid-template-columns:minmax(0,760px);justify-content:center}.chart-grid.single>:last-child{grid-column:auto}@media(max-width:900px){.dashboard{padding:18px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.chart-grid{grid-template-columns:1fr}.chart-grid>:last-child,.chart-grid .wide{grid-column:auto}.tabs{width:100%;overflow:auto;justify-content:flex-start}}@media(max-width:520px){.kpis,.utility-cards{grid-template-columns:1fr}.dashboard-header{align-items:flex-start}.tabs button{white-space:nowrap}}
</style>
