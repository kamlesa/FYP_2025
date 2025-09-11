<script setup>
import Header from './components/Header.vue'
</script>

<template>
  <div class="flex flex-col h-screen justify-between bg-backblue">
    <link href="/dist/output.css" rel="stylesheet" />
    <header class><Header></Header></header>
    <main class="mb-auto p-[1rem] bg-happygreen">
      <router-view></router-view>
    </main>
    <footer class=""><p>Footer</p></footer>
  </div>
</template>

<style scoped></style>
