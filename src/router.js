import { createRouter, createWebHistory } from 'vue-router'
import AboutPage from './pages/AboutPage.vue'
import ContactPage from './pages/ContactPage.vue'
import Semester1 from './pages/Semester1.vue'
import Dashboard from './pages/Dashboard.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/about', component: AboutPage },
  { path: '/contact', component: ContactPage },
  { path: '/fit4701', component: Semester1 },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
