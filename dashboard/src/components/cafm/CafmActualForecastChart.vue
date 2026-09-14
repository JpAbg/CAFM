<script setup>
import { computed, ref, watch } from 'vue'
import { LineChart } from 'frappe-ui/charts'
const props=defineProps({series:{type:Array,default:()=>[]},colors:{type:Array,default:()=>[]},title:String,subtitle:String})
const selectedIndex=ref(0)
watch(()=>props.series,()=>{selectedIndex.value=0})
const selected=computed(()=>props.series[selectedIndex.value]||{labels:[],actual:[],forecast:[],unit:'Usage'})
const color=computed(()=>props.colors[selectedIndex.value]||'#2E86DE')
const rows=computed(()=>selected.value.labels.map((month,index)=>({month,actual:selected.value.actual[index],forecast:selected.value.forecast[index]})))
const seriesConfig=computed(()=>({actual:{label:'Actual '+selected.value.utility_type,color:color.value,smooth:true,showDataPoints:true},forecast:{label:'Forecast '+selected.value.utility_type,color:color.value,lineType:'dotted',lineWidth:2,smooth:true,showDataPoints:true}}))
</script>
<template>
<section class="cafm-chart">
  <LineChart :data="rows" x="month" :y="['actual','forecast']" :x-axis="{type:'time',timeGrain:'month',title:'Month'}" :y-axis="{title:selected.unit}" :series-config="seriesConfig" :title="title" :subtitle="subtitle">
    <template #actions><label class="series-picker"><span>Utility</span><select v-model.number="selectedIndex"><option v-for="(item,index) in series" :key="item.utility_type" :value="index">{{item.utility_type}} ({{item.unit}})</option></select></label></template>
  </LineChart>
</section>
</template>
<style scoped>
.cafm-chart{height:360px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}.series-picker{display:flex;align-items:center;gap:7px;color:#547187;font-size:12px}.series-picker select{border:1px solid #c9dbe7;border-radius:8px;background:#f7fbfd;color:#173650;padding:6px 28px 6px 9px;font-size:12px}
</style>
