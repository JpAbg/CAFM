<script setup>
import { HeatmapChart } from 'frappe-ui/charts'

defineProps({
  data: { type: Array, default: () => [] },
})
</script>

<template>
  <section class="cafm-chart">
    <HeatmapChart
      :data="data"
      x="week"
      y="day"
      value="plans"
      palette="sequential"
      :min="0"
      :format="(value) => `${value} planned task${value === 1 ? '' : 's'}`"
      title="Preventive maintenance calendar"
      subtitle="Active plans grouped by their next scheduled due date"
    />
  </section>
</template>

<style scoped>
.cafm-chart {
  height: 330px;
  padding: 16px;
  border: 1px solid #dce7ee;
  border-radius: 14px;
  background: #fff;
}
</style>
