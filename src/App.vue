<script setup>
import Header from './components/Header.vue'
</script>

<template>
  <div class="flex flex-col h-screen justify-between bg-backblue bg-offwhite">
    <link href="/dist/output.css" rel="stylesheet" />
    <header class="bg-deepaqua text-offwhite"><Header></Header></header>
    <main class="mb-auto p-[1rem] bg-offwhite">
      <router-view></router-view>
    </main>
    <footer class="bg-midblue"><p>Footer</p></footer>
  </div>
</template>

<style scoped></style>
