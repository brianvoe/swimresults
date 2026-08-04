import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { title: 'NASH Results — Nashville Adult Swim League' },
  },
  {
    path: '/swimmers',
    name: 'swimmers',
    component: () => import('../views/SwimmersView.vue'),
    meta: { title: 'Swimmers — NASH Results' },
  },
  {
    path: '/swimmer/:slug',
    name: 'swimmer',
    component: () => import('../views/SwimmerView.vue'),
  },
  {
    path: '/meet/:id',
    name: 'meet',
    component: () => import('../views/MeetView.vue'),
  },
  {
    path: '/team/:slug',
    name: 'team',
    component: () => import('../views/TeamView.vue'),
  },
  {
    path: '/leaderboards',
    name: 'leaderboards',
    component: () => import('../views/LeaderboardsView.vue'),
    meta: { title: 'Leaderboards — NASH Results' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: 'Not found — NASH Results' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    if (to.path === from.path) return {}
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  if (title) document.title = title
})
