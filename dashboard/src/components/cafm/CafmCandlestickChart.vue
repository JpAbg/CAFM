<script setup>
import { computed, ref } from 'vue'
import { CandlestickChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { ChartContainer, registerChartModules, useChart, useChartTokens } from 'frappe-ui/charts'
const props=defineProps({source:{type:Object,default:()=>({})},title:String,subtitle:String})
registerChartModules([CandlestickChart,GridComponent,TooltipComponent])
const plotEl=ref()
const {tokens}=useChartTokens(plotEl)
const option=computed(()=>({animation:true,grid:{left:52,right:20,top:18,bottom:42},tooltip:{trigger:'axis'},xAxis:{type:'category',data:(props.source.candles||[]).map(item=>item.label),axisLine:{lineStyle:{color:tokens.value.axisLine}},axisLabel:{color:tokens.value.axisLabel}},yAxis:{type:'value',name:props.source.unit||'Usage',splitLine:{lineStyle:{color:tokens.value.splitLine}},axisLabel:{color:tokens.value.axisLabel}},series:[{type:'candlestick',name:props.source.meter_label||'Monthly usage',data:(props.source.candles||[]).map(item=>[item.open,item.close,item.low,item.high]),itemStyle:{color:'#22C55E',color0:'#DC2626',borderColor:'#16A34A',borderColor0:'#B91C1C'}}]}))
useChart({container:plotEl,option:()=>option.value})
</script>
<template><section class="cafm-chart"><ChartContainer :title="title" :subtitle="subtitle" :empty="!(source.candles||[]).length"><div ref="plotEl" class="h-full w-full rounded-2" /></ChartContainer></section></template>
<style scoped>.cafm-chart{height:350px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}</style>
