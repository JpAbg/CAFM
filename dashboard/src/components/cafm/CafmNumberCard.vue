<script setup>
import { computed, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'

const props = defineProps({
  title: String,
  value: [Number, String],
  suffix: String,
  prefix: String,
  target: Number,
  compact: Boolean,
  precision: Number,
  delta: Number,
  deltaSuffix: { type: String, default: '%' },
  deltaCaption: { type: String, default: 'vs prior month' },
  negativeIsBetter: Boolean,
  trend: Array,
  trendType: String,
  color: String,
  selectableComparison: Boolean,
})

const comparison = ref(1)
const comparisonLabels = {
  1: 'last month',
  3: '3 months ago',
  5: '5 months ago',
}
const periodOptions = [1, 3, 5].map((months) => ({
  label: `vs ${comparisonLabels[months]}`,
  onClick: () => {
    comparison.value = months
  },
}))

const comparisonDelta = computed(() => {
  if (!props.selectableComparison || !props.trend?.length) return props.delta
  const current = Number(props.trend.at(-1))
  const baseline = Number(props.trend.at(-(comparison.value + 1)))
  if (!Number.isFinite(current) || !Number.isFinite(baseline) || baseline === 0) {
    return null
  }
  return Number((((current - baseline) / Math.abs(baseline)) * 100).toFixed(1))
})

const sparkline = computed(() =>
  props.trend?.length
    ? {
        data: props.trend,
        color: props.color,
        type: props.trendType || 'line',
      }
    : undefined,
)
</script>

<template>
  <NumberCard
    class="cafm-number-card"
    :title="title"
    :value="value"
    :suffix="suffix"
    :prefix="prefix"
    :target="target"
    :compact="compact"
    :precision="precision"
    :delta="comparisonDelta"
    :delta-suffix="deltaSuffix"
    :delta-caption="selectableComparison ? undefined : deltaCaption"
    :negative-is-better="negativeIsBetter"
    :color="color"
    :sparkline="sparkline"
  >
    <template v-if="selectableComparison" #caption>
      <Dropdown :options="periodOptions" placement="left">
        <button type="button" class="comparison-button">
          <span>vs {{ comparisonLabels[comparison] }}</span>
          <svg class="comparison-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
        </button>
      </Dropdown>
    </template>
  </NumberCard>
</template>

<style scoped>
:deep(.cafm-number-card[data-slot="chart-card"]) {
  height: 96px;
  padding: 8px 12px;
}
:deep(.cafm-number-card .pb-10) {
  padding-bottom: 20px;
}
:deep(.cafm-number-card .h-12) {
  height: 24px;
}
.comparison-button {
  display: flex;
  height: 20px;
  min-width: 0;
  align-items: center;
  gap: 4px;
  margin: 0 -4px;
  padding: 0 4px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}
.comparison-chevron { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.comparison-button:hover {
  background: #edf4f8;
  color: #173650;
}
</style>
