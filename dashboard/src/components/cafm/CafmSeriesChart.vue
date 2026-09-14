<script setup>
import { computed, ref, watch } from 'vue'
import { AreaChart, BarChart, LineChart } from 'frappe-ui/charts'
const props=defineProps({source:{type:Object,default:()=>({})},kind:{type:String,default:'bar'},title:String,subtitle:String,horizontal:Boolean,unit:String,palette:Array,selectable:Boolean})
const components={bar:BarChart,line:LineChart,area:AreaChart}
const chartComponent=computed(()=>components[props.kind]||BarChart)
const selectedIndex=ref(0)
watch(()=>props.source,()=>{selectedIndex.value=0})
const allDatasets=computed(()=>props.source.datasets||[])
const activeDatasets=computed(()=>props.selectable?(allDatasets.value[selectedIndex.value]?[allDatasets.value[selectedIndex.value]]:[]):allDatasets.value)
const rows=computed(()=>{const labels=props.source.labels||[];return labels.map((label,index)=>{const row={label};activeDatasets.value.forEach((dataset,seriesIndex)=>{row['series'+seriesIndex]=dataset.values?.[index]??0});return row})})
const series=computed(()=>activeDatasets.value.map((_,index)=>'series'+index))
const config=computed(()=>Object.fromEntries(activeDatasets.value.map((item,index)=>['series'+index,{label:item.name,smooth:props.kind!=='bar'}])))
const activePalette=computed(()=>props.selectable&&props.palette?[props.palette[selectedIndex.value]||props.palette[0]]:(props.palette||'categorical'))
</script>
<template>
<section class="cafm-chart">
  <component :is="chartComponent" :data="rows" x="label" :y="series" :horizontal="horizontal" :x-axis="{type:'category'}" :y-axis="{title:unit||''}" :series-config="config" :palette="activePalette" :title="title" :subtitle="subtitle">
    <template v-if="selectable&&allDatasets.length" #actions><label class="series-picker"><span>Utility</span><select v-model.number="selectedIndex"><option v-for="(dataset,index) in allDatasets" :key="dataset.name" :value="index">{{dataset.name}}</option></select></label></template>
  </component>
</section>
</template>
<style scoped>
.cafm-chart{height:340px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}
.series-picker{display:flex;align-items:center;gap:7px;color:#547187;font-size:12px}.series-picker select{max-width:220px;border:1px solid #c9dbe7;border-radius:8px;background:#f7fbfd;color:#173650;padding:6px 28px 6px 9px;font-size:12px}
</style>
