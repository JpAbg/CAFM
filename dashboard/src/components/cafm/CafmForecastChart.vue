<script setup>
import { LineChart } from 'frappe-ui/charts'
defineProps({ data:Array,title:String,unit:String })
</script>
<template><section class="cafm-chart"><LineChart :data="data" x="month" :y="['actual','forecast']" :x-axis="{ type: 'time', timeGrain: 'month' }" :y-axis="{ title: unit || 'Usage' }" :series-config="{ actual:{ smooth:true }, forecast:{ lineType:'dashed', smooth:true } }" :title="title" subtitle="Actual versus forecast" /></section></template>
<style scoped>.cafm-chart{height:320px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}</style>