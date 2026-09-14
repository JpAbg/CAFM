<script setup>
import { computed, ref } from 'vue'
import { FunnelChart } from 'frappe-ui/charts'

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const selectedStage = ref(null)
const stages = computed(() =>
  props.data.map((row) => ({
    stage: row.label,
    count: row.value,
  })),
)
</script>

<template>
  <section class="cafm-funnel">
    <div class="cafm-funnel-chart">
      <FunnelChart
        :data="stages"
        category="stage"
        value="count"
        :show-percentages="false"
        title="Work orders by category"
        subtitle="Current work-order volume by maintenance category"
        @select="selectedStage = $event"
      />
    </div>
    <p class="cafm-selection">
      <template v-if="selectedStage">
        Selected {{ selectedStage.label }} - {{ selectedStage.value }} work orders
      </template>
      <template v-else>Select a category to inspect its total.</template>
    </p>
  </section>
</template>

<style scoped>
.cafm-funnel {
  height: 330px;
  padding: 16px;
  border: 1px solid #dce7ee;
  border-radius: 14px;
  background: #fff;
}
.cafm-funnel-chart {
  height: 260px;
}
.cafm-selection {
  margin: 8px 4px 0;
  color: #6e8496;
  font-size: 13px;
}
</style>
