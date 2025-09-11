<template>
  <div class="max-w-7xl mx-auto flex items-center justify-between p-4">
    <!-- Logo + Title -->
    <div class="flex items-center space-x-3">
      <!-- <img src="your-logo.png" alt="Logo" class="w-10 h-10 rounded-full" /> -->
      <h1 class="text-xl font-bold">FIT4701/4702 FYP Project Monash</h1>
    </div>

    <!-- Navigation -->
    <nav class="space-x-6 hidden sm:block">
      <router-link
        to="/"
        class="font-semibold px-4 py-2 rounded-lg hover:text-cadetblue hover:bg-calmblue"
        >Dashboard</router-link
      >
      <router-link
        to="/fit4701"
        class="font-semibold px-4 py-2 rounded-lg hover:text-cadetblue hover:bg-calmblue"
        >FIT4701</router-link
      >
      <router-link
        to="/about"
        class="font-semibold px-4 py-2 rounded-lg hover:text-cadetblue hover:bg-calmblue"
        >About</router-link
      >
      <router-link
        to="/contact"
        class="font-semibold px-4 py-2 rounded-lg hover:text-cadetblue hover:bg-calmblue"
        >Contact</router-link
      >
    </nav>
  </div>
</template>

<script setup>
import { ref } from 'vue'
</script>
