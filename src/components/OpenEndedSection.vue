<template>
  <div class="mb-10">
    <p class="font-semibold text-lg mb-2">Open Ended Personal Thoughts</p>
  </div>
  <div ref="chart"></div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import embed from 'vega-embed'
import topTermsQ from '../assets/schema_top_terms_questions.json'
import topTerms from '../assets/schema_top_terms.json'
import bubble from '../assets/schema_bubble.json'

const chart = ref(null)

onMounted(() => {
  const spec = topTerms

  embed(chart.value, spec, {
    actions: { export: true, source: true, compiled: true, editor: true },
  })
})
</script>
