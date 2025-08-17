import { createRouter, createWebHistory } from 'vue-router';
import Index from '../pages/Index.vue';
import Monitor from '../pages/Monitor.vue';
import Items from '../pages/Items.vue';
import Cpus from '../pages/Cpus.vue';
import Tasks from '../pages/Tasks.vue';
import Automate from '../pages/Automate.vue';
import Settings from '../pages/Settings.vue';
import Info from '../pages/Info.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Index,
  },
  {
    path: '/index',
    name: 'Index',
    component: Index,
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: Monitor,
  },
  {
    path: '/items',
    name: 'Items',
    component: Items,
  },
  {
    path: '/cpus',
    name: 'Cpus',
    component: Cpus,
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: Tasks,
  },
  {
    path: '/automate',
    name: 'Automate',
    component: Automate,
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
  },
  {
    path: '/info',
    name: 'Info',
    component: Info,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
