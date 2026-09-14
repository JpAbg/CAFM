<script setup>
import { BarChart } from 'frappe-ui/charts'
defineProps({ data: { type: Array, required: true }, title: String, subtitle: String, unit: String })
</script>
<template><section class="cafm-chart"><BarChart :data="data" x="month" :y="['electricity','water','gas','fuel']" :x-axis="{ type: 'time', timeGrain: 'month' }" :y-axis="{ title: unit || 'Usage' }" palette="categorical" :title="title" :subtitle="subtitle" /></section></template>
<style scoped>.cafm-chart{height:320px;padding:16px;border:1px solid #dce7ee;border-radius:14px;background:#fff}</style>