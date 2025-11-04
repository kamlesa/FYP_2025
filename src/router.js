import { createRouter, createWebHistory } from 'vue-router'

// Eager load frequently-used pages if you want
import Dashboard from '@/pages/Dashboard.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL), // important
  routes: [
    { path: '/', name: 'Dashboard', component: Dashboard },
    { path: '/open-ended', name: 'OpenEnded', component: () => import('@/pages/OpenEnded.vue') },
    { path: '/test', name: 'Test', component: () => import('@/pages/Testing.vue') },

    // optional: other pages you already have
    { path: '/fit4701', name: 'FIT4701', component: () => import('@/pages/Semester1.vue') },
    { path: '/about', name: 'About', component: () => import('@/pages/AboutPage.vue') },
    { path: '/contact', name: 'Contact', component: () => import('@/pages/ContactPage.vue') },

    // fallback
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router

