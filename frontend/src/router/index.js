import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Report from '../views/Report.vue'
import History from '../views/History.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/report/:id',
    name: 'Report',
    component: Report,
    props: true
  },
  {
    path: '/history',
    name: 'History',
    component: History
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
