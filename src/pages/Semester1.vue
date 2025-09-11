<template>
  <div class="sectionpage">
    <h2 class="sectionheading">Semester 1 Work</h2>
    <p>
      Due to unfortunate circumstances, the project was altered midway, on this page we are
      displaying progress from the previous half of the project
    </p>
    <p>This is temporarily here.. for testing</p>

    <h2 class="sectionheading">
      AI-Driven Sentiment Analysis for Public Perception of Emerging Technologies
    </h2>
  </div>
  <div id="vis"></div>
</template>

<script setup>
import { onMounted } from 'vue'
import vegaEmbed from 'vega-embed'

const spec = {
  $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
  description: 'Grouped bar chart of sentiment counts (positive, neutral, negative) by video ID.',
  width: 800,
  height: 400,
  data: {
    url: 'data/testing_saketh.json',
    format: { type: 'json' },
  },
  transform: [
    {
      fold: ['positive', 'neutral', 'negative'],
      as: ['sentiment', 'count'],
    },
  ],
  mark: {
    type: 'bar',
  },
  encoding: {
    x: { field: 'videoId', type: 'nominal', title: 'Video ID' },
    xOffset: { field: 'sentiment' },
    y: { field: 'count', type: 'quantitative', title: 'Comment Count' },
    color: { field: 'sentiment', type: 'nominal', title: 'Sentiment' },
    tooltip: [
      { field: 'videoId', type: 'nominal' },
      { field: 'sentiment', type: 'nominal' },
      { field: 'count', type: 'quantitative' },
    ],
  },
}

onMounted(() => {
  vegaEmbed('#vis', spec)
})
</script>
