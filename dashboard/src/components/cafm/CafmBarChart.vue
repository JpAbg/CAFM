<script setup>
import { computed } from 'vue'
import { BarChart } from 'frappe-ui/charts'

const props = defineProps({
  data: { type: Array, required: true },
  title: String,
  subtitle: String,
  horizontal: Boolean,
  unit: String,
  palette: [Array, String],
  multiColor: Boolean,
})

const fallbackColors = [
  '#4463F0',
  '#22B8CF',
  '#F59E0B',
  '#22C55E',
  '#8B5CF6',
  '#E65100',
  '#E53935',
  '#64748B',
]

const barColors = computed(() =>
  Array.isArray(props.palette) && props.palette.length > 1
    ? props.palette
    : fallbackColors,
)

const seriesConfig = computed(() => ({
  value: {
    label: props.unit || 'Work orders',
    showDataLabels: true,
    ...(props.multiColor
      ? {
          echartOptions: {
            itemStyle: {
              color: (params) =>
                barColors.value[params.dataIndex % barColors.value.length],
            },
          },
        }
      : {}),
  },
}))
</script>

<template>
  <section class="cafm-chart">
    <BarChart
      :data="data"
      x="label"
      y="value"
      :horizontal="horizontal"
      :y-axis="{ title: unit || 'Work orders' }"
      :series-config="seriesConfig"
      :title="title"
      :subtitle="subtitle"
      :palette="palette"
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
