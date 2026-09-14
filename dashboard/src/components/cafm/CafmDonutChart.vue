<script setup>
import { computed } from 'vue'
import { DonutChart } from 'frappe-ui/charts'
const props=defineProps({data:Array,title:String,subtitle:String,centerLabel:String,palette:[Array,String],variant:String,showInlineLabels:Boolean,colorMap:Object,orderedLegend:Boolean})
const colorFor=(label)=>props.colorMap?.[String(label||'').toLowerCase()]||'#64748B'
const chartPalette=computed(()=>{if(!props.colorMap)return props.palette;return [...(props.data||[])].sort((left,right)=>(Number(right.value)||0)-(Number(left.value)||0)).map(row=>colorFor(row.label))})
</script>
<template>
<section class="cafm-chart" :class="{'custom-legend':orderedLegend}">
  <DonutChart :data="data" category="label" value="value" :title="title" :subtitle="subtitle" :center-label="centerLabel" :palette="chartPalette" :variant="variant" :show-inline-labels="showInlineLabels" />
  <div v-if="orderedLegend" class="ordered-legend" aria-label="Chart legend">
    <div v-for="row in data" :key="row.label" class="legend-item"><span class="legend-dot" :style="{backgroundColor:colorFor(row.label)}"></span><span>{{row.label}}</span><strong>{{row.value}}</strong></div>
  </div>
</section>
</template>
<style scoped>
.cafm-chart{height:320px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}
.custom-legend{height:320px;display:flex;min-height:0;flex-direction:column;padding-bottom:14px}
.custom-legend :deep([data-slot="chart-container"]){height:auto;min-height:0;flex:1}.custom-legend :deep([data-slot="chart-legend"]){display:none}
.ordered-legend{display:flex;flex-wrap:wrap;justify-content:center;gap:8px 18px;flex:0 0 auto;min-height:24px;margin-top:8px;padding:0 8px;color:#47647a;font-size:12px}
.legend-item{display:flex;align-items:center;gap:6px}.legend-item strong{color:#173650;font-variant-numeric:tabular-nums}.legend-dot{width:9px;height:9px;border-radius:50%;flex:0 0 9px}
</style>
