import Vue from 'vue'
import App from './App.vue'
import VueRouter from 'vue-router'
import 'leaflet/dist/leaflet.css'

// Import router views
import MapView from './views/MapView.vue'
import DepotsView from './views/DepotsView.vue'
import CouriersView from './views/CouriersView.vue'
import OrdersView from './views/OrdersView.vue'
import OptimizeView from './views/OptimizeView.vue'

// Use VueRouter
Vue.use(VueRouter)

// Create router instance
const router = new VueRouter({
  mode: 'history',
  routes: [
    { path: '/', component: MapView },
    { path: '/depots', component: DepotsView },
    { path: '/couriers', component: CouriersView },
    { path: '/orders', component: OrdersView },
    { path: '/optimize', component: OptimizeView }
  ]
})

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')
