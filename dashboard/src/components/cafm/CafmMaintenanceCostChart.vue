<script setup>
import { BarChart } from 'frappe-ui/charts'

defineProps({
  data: { type: Array, default: () => [] },
})
</script>

<template>
  <section class="cafm-chart">
    <BarChart
      :data="data"
      x="site"
      y="amount"
      series="cost_type"
      :max-series="4"
      :y-axis="{ title: 'Maintenance cost' }"
      :series-config="{
        'Material cost': { label: 'Material cost' },
        'External service cost': { label: 'External service cost' },
      }"
      palette="categorical"
      title="Maintenance cost by site"
      subtitle="Material and external-service costs recorded on work orders"
    />
  </section>
</template>

<style scoped>
.cafm-chart {
  height: 360px;
  padding: 16px;
  border: 1px solid #dce7ee;
  border-radius: 14px;
  background: #fff;
}
</style>
