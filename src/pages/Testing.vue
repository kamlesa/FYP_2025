<template>
  <div class="sectionpage text-center">
    <p class="sectionheading">Dashboard</p>

    <!-- quantitative components -->
    <ScoresChart />
    <LikertChart />
    <SpiderChart />
    <ColourPalette />

    <!-- Open-Ended Analysis -->
    <p class="sectionheading mt-12">Open-Ended Analysis</p>

    <section class="max-w-6xl mx-auto text-left">
      <div class="mb-10">
        <p class="font-semibold mb-2">TF-IDF Top Terms per Question</p>
        <div ref="tfidfPerQ"></div>
      </div>

      <div class="mb-10">
        <p class="font-semibold mb-2">Common Ethical Concerns (Frequency)</p>
        <div ref="concernFreq"></div>
      </div>

      <div class="mb-10">
        <p class="font-semibold mb-2">Sentiment Distribution (Open-Ended)</p>
        <div ref="sentimentChart"></div>
      </div>

      <!-- Any error from the embeds will show here -->
      <pre ref="errLog" class="text-red-600 whitespace-pre-wrap"></pre>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, nextTick } from 'vue'
import embed from 'vega-embed'

/* your existing components */
import ColourPalette from '@/components/ColourPalette.vue'
import ScoresChart   from '@/components/ScoresChart.vue'
import LikertChart   from '@/components/LikertChart.vue'
import SpiderChart   from '@/components/SpiderChart.vue'

/* JSON Vega-Lite specs (paths must exist) */
import tfidfPerQSpec from '@/assets/schema_tfidf_per_question.json'
import concernsSpec  from '@/assets/schema_concerns_frequency.json'
import sentimentSpec from '@/assets/schema_sentiment_distribution.json'

/* refs for the three charts + error display */
const tfidfPerQ      = ref(null)
const concernFreq    = ref(null)
const sentimentChart = ref(null)
const errLog         = ref(null)

/* helper: safe-embed that writes errors instead of crashing render */
async function safeEmbed(targetEl, spec, name){
  if (!targetEl) return
  try {
    await embed(targetEl, spec, { actions: false })
  } catch (e) {
    const msg = `[${name}] ${e?.message || e}`
    console.error(msg, e)
    if (errLog.value) {
      errLog.value.textContent += (errLog.value.textContent ? '\n' : '') + msg
    }
  }
}

onMounted(async () => {
  await nextTick()
  await safeEmbed(tfidfPerQ.value,      tfidfPerQSpec, 'TF-IDF')
  await safeEmbed(concernFreq.value,     concernsSpec,  'Concerns')
  await safeEmbed(sentimentChart.value,  sentimentSpec, 'Sentiment')
})
</script>

<style scoped>
.sectionheading {
  @apply text-2xl font-semibold my-6;
}
.sectionpage {
  @apply px-4 md:px-8;
}
</style>
