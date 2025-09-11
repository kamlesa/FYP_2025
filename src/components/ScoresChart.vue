<template>
  <div class="p-6">
    <h2 class="text-2xl font-bold mb-4 text-midblue">Scores Chart</h2>
    <div ref="chart"></div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import embed from 'vega-embed'
import specs from '../assets/schema_scoring.json'
const chart = ref(null)

onMounted(() => {
  const spec = specs

  embed(chart.value, spec, {
    actions: { export: true, source: true, compiled: true, editor: true },
  })
})
</script>
