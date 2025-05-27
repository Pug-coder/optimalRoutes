<template>
  <div class="optimize-view">
    <h2>Оптимизация маршрутов</h2>
    
    <div class="optimization-container">
      <!-- Optimization settings -->
      <div class="card">
        <h3>Настройки оптимизации</h3>
        <div class="form-container">
          <div class="form-group">
            <label for="algorithm">Алгоритм оптимизации</label>
            <select id="algorithm" v-model="settings.algorithm">
              <option value="nearest_neighbor">Ближайший сосед (быстрый)</option>
              <option value="or_tools">Google OR-Tools (точный)</option>
              <option value="genetic">Генетический алгоритм (эвристический)</option>
            </select>
          </div>
          
          <div v-if="settings.algorithm === 'genetic'" class="genetic-settings">
            <div class="form-row">
              <div class="form-group">
                <label for="population-size">Размер популяции</label>
                <input type="number" id="population-size" v-model.number="settings.genetic.population_size" min="10" step="10">
              </div>
              <div class="form-group">
                <label for="generations">Количество поколений</label>
                <input type="number" id="generations" v-model.number="settings.genetic.generations" min="10" step="10">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="mutation-rate">Вероятность мутации</label>
                <input type="number" id="mutation-rate" v-model.number="settings.genetic.mutation_rate" min="0.01" max="1" step="0.01">
              </div>
              <div class="form-group">
                <label for="elite-size">Размер элиты</label>
                <input type="number" id="elite-size" v-model.number="settings.genetic.elite_size" min="1" step="1">
              </div>
            </div>
          </div>
          
          <div class="algorithm-description">
            <div v-if="settings.algorithm === 'nearest_neighbor'" class="desc-box">
              <strong>Ближайший сосед</strong> - быстрый алгоритм, который строит маршрут, всегда выбирая ближайшую непосещенную точку.
              Подходит для быстрого получения приемлемого результата.
            </div>
            <div v-else-if="settings.algorithm === 'or_tools'" class="desc-box">
              <strong>Google OR-Tools</strong> - эффективный алгоритм для точного решения задачи маршрутизации транспорта.
              Хорошо работает с небольшим и средним количеством заказов (до нескольких сотен).
            </div>
            <div v-else class="desc-box">
              <strong>Генетический алгоритм</strong> - эвристический метод, который может находить приемлемые решения
              для больших задач маршрутизации. Не гарантирует оптимальность, но работает быстрее для сложных случаев.
            </div>
          </div>
          
          <div class="form-group form-check">
            <input type="checkbox" id="reset-previous" v-model="settings.resetPrevious">
            <label for="reset-previous">Сбросить предыдущие маршруты</label>
          </div>
          
          <div class="stats-box">
            <div class="stat-item">
              <span class="stat-label">Всего заказов:</span>
              <span class="stat-value">{{ stats.orderCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Нераспределённых заказов:</span>
              <span class="stat-value">{{ stats.unassignedCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Доступно курьеров:</span>
              <span class="stat-value">{{ stats.courierCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Количество складов:</span>
              <span class="stat-value">{{ stats.depotCount }}</span>
            </div>
          </div>
          
          <button @click="runOptimization" :disabled="optimizing" class="btn-primary">
            {{ optimizing ? 'Оптимизация...' : 'Запустить оптимизацию' }}
          </button>
        </div>
      </div>
      
      <!-- Optimization results -->
      <div class="card results-card">
        <h3>Результаты оптимизации</h3>
        
        <div v-if="optimizing" class="loading-container">
          <div class="loading-spinner"></div>
          <p>Выполняется оптимизация маршрутов...</p>
          <p class="small">Это может занять от нескольких секунд до нескольких минут в зависимости от объема данных</p>
        </div>
        
        <div v-else-if="!lastResult" class="empty-result">
          <p>Нет результатов оптимизации</p>
          <p class="small">Запустите оптимизацию, чтобы увидеть результаты</p>
        </div>
        
        <div v-else class="optimization-results">
          <div class="result-summary">
            <div class="summary-item">
              <span class="label">Алгоритм:</span>
              <span class="value">{{ getAlgorithmDisplayName(lastResult.algorithm) }}</span>
            </div>
            <div class="summary-item">
              <span class="label">Всего маршрутов:</span>
              <span class="value">{{ lastResult.routes.length }}</span>
            </div>
            <div class="summary-item">
              <span class="label">Распределено заказов:</span>
              <span class="value">{{ lastResult.assigned_orders }} из {{ lastResult.total_orders }}</span>
            </div>
            <div class="summary-item">
              <span class="label">Общее расстояние:</span>
              <span class="value">{{ lastResult.total_distance.toFixed(2) }} км</span>
            </div>
            <div class="summary-item">
              <span class="label">Время выполнения:</span>
              <span class="value">{{ lastResult.execution_time.toFixed(2) }} с</span>
            </div>
          </div>
          
          <div class="routes-header">
            <h4>Созданные маршруты</h4>
            <div class="routes-controls">
              <button @click="expandAllRoutes" class="btn-outline small">Развернуть все</button>
              <button @click="collapseAllRoutes" class="btn-outline small">Свернуть все</button>
            </div>
          </div>
          <div class="routes-accordion">
            <div v-for="route in lastResult.routes" :key="route.id" class="route-accordion-item">
              <div class="route-accordion-header" @click="toggleRoute(route.id)">
                <div class="route-summary">
                  <div class="route-title">
                    <i class="chevron-icon" :class="{ 'expanded': expandedRoutes.includes(route.id) }">▼</i>
                    Маршрут #{{ route.id }} - {{ getCourierName(route.courier_id) }}
                  </div>
                  <div class="route-metrics">
                    <span class="metric-badge orders">{{ route.points.length }} из {{ getCourierInfo(route.courier_id).max_capacity }} заказов</span>
                    <span class="metric-badge distance">{{ route.total_distance.toFixed(2) }} из {{ getCourierInfo(route.courier_id).max_distance }} км</span>
                    <span class="metric-badge weight">{{ route.total_weight.toFixed(2) }} из {{ getCourierInfo(route.courier_id).max_weight }} кг</span>
                  </div>
                </div>
              </div>
              <div class="route-accordion-content" :class="{ 'expanded': expandedRoutes.includes(route.id) }">
                <div class="route-details">
                  <div class="depot-info">
                    <div class="depot-marker">D</div>
                    <span>Склад: {{ getDepotName(route.depot_id) }}</span>
                  </div>
                  <div class="route-path">
                    <div v-for="(point, index) in route.points" :key="index" class="route-step">
                      <div class="step-number">{{ index + 1 }}</div>
                      <div class="step-info">
                        <div class="order-info">
                          <strong>Заказ #{{ point.order_id }}</strong>
                        </div>
                        <div class="order-details" v-if="getOrderDetails(point.order_id)">
                          <span>{{ getOrderDetails(point.order_id).customer_name || 'Клиент' }}</span>
                          <span>{{ getOrderDetails(point.order_id).weight || 0 }} кг</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="depot-info return">
                    <div class="depot-marker">D</div>
                    <span>Возврат в склад</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="actions">
            <router-link to="/" class="btn-secondary">Показать на карте</router-link>
            <button @click="resetRoutes" class="btn-outline">Сбросить все маршруты</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { API_BASE_URL } from '../config'

export default {
  name: 'OptimizeView',
  data() {
    return {
      settings: {
        algorithm: 'nearest_neighbor',
        resetPrevious: true,
        genetic: {
          population_size: 100,
          generations: 100,
          mutation_rate: 0.1,
          elite_size: 20
        }
      },
      optimizing: false,
      lastResult: null,
      stats: {
        orderCount: 0,
        unassignedCount: 0,
        courierCount: 0,
        depotCount: 0
      },
      depots: [],
      couriers: [],
      expandedRoutes: [],
      orders: []
    }
  },
  mounted() {
    this.fetchStats()
  },
  methods: {
    async fetchStats() {
      try {
        // Fetch depots
        const depotsResponse = await axios.get(`${API_BASE_URL}/depots`)
        this.depots = depotsResponse.data
        this.stats.depotCount = this.depots.length
        
        // Fetch couriers
        const couriersResponse = await axios.get(`${API_BASE_URL}/couriers`)
        this.couriers = couriersResponse.data
        this.stats.courierCount = this.couriers.length
        
        // Fetch orders
        const ordersResponse = await axios.get(`${API_BASE_URL}/orders`)
        this.orders = ordersResponse.data
        
        // Fetch order counts
        const ordersCountResponse = await axios.get(`${API_BASE_URL}/orders/count`)
        this.stats.orderCount = ordersCountResponse.data.count
        
        // Fetch unassigned order count
        const unassignedResponse = await axios.get(`${API_BASE_URL}/orders/count?assigned=false`)
        this.stats.unassignedCount = unassignedResponse.data.count
        
        // Fetch latest optimization result
        const routesResponse = await axios.get(`${API_BASE_URL}/routes`)
        if (routesResponse.data && routesResponse.data.length > 0 && !this.lastResult) {
          // Try to restore from localStorage first
          const savedResult = localStorage.getItem('lastOptimizationResult')
          if (savedResult) {
            try {
              const parsedResult = JSON.parse(savedResult)
              // Verify that the saved result matches current routes
              if (parsedResult.routes && parsedResult.routes.length === routesResponse.data.length) {
                this.lastResult = {
                  ...parsedResult,
                  routes: routesResponse.data // Use fresh route data from API
                }
                return
              }
            } catch (e) {
              console.warn('Failed to parse saved optimization result:', e)
            }
          }
          
          // Fallback: Mock a result object since we don't store the full optimization result
          // Only set if there's no existing optimization result
          this.lastResult = {
            algorithm: 'unknown',
            routes: routesResponse.data,
            assigned_orders: this.stats.orderCount - this.stats.unassignedCount,
            total_orders: this.stats.orderCount,
            total_distance: routesResponse.data.reduce((total, route) => total + route.total_distance, 0),
            execution_time: 0
          }
        }
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    },
    getDepotName(depotId) {
      const depot = this.depots.find(d => d.id === depotId)
      return depot ? depot.name : `Склад #${depotId}`
    },
    getCourierName(courierId) {
      const courier = this.couriers.find(c => c.id === courierId)
      return courier ? courier.name : `Курьер #${courierId}`
    },
    getCourier(courierId) {
      const courier = this.couriers.find(c => c.id === courierId)
      return courier || { name: `Курьер #${courierId}`, max_weight: 0 }
    },
    getCourierInfo(courierId) {
      const courier = this.couriers.find(c => c.id === courierId)
      return courier || { 
        name: `Курьер #${courierId}`, 
        max_capacity: 0, 
        max_weight: 0, 
        max_distance: 0 
      }
    },
    async runOptimization() {
      if (this.optimizing) return
      
      try {
        this.optimizing = true
        
        // Reset routes if needed
        if (this.settings.resetPrevious) {
          await axios.post(`${API_BASE_URL}/routes/reset`)
        }
        
        // Run optimization
        let response;
        
        if (this.settings.algorithm === 'genetic') {
          // For genetic algorithm, use separate endpoint with body parameters
          response = await axios.post(`${API_BASE_URL}/routes/optimize/genetic`, {
            population_size: this.settings.genetic.population_size,
            generations: this.settings.genetic.generations,
            mutation_rate: this.settings.genetic.mutation_rate,
            elite_size: this.settings.genetic.elite_size
          });
        } else {
          // For other algorithms, use main endpoint with JSON body parameters
          response = await axios.post(`${API_BASE_URL}/routes/optimize`, {
            algorithm: this.settings.algorithm
          });
        }
        
        // API now returns OptimizationResponse with algorithm info
        this.lastResult = {
          algorithm: response.data.algorithm,
          routes: response.data.routes,
          assigned_orders: response.data.assigned_orders,
          total_orders: response.data.total_orders,
          total_distance: response.data.total_distance,
          execution_time: response.data.execution_time
        };
        
        // Save optimization result to localStorage
        localStorage.setItem('lastOptimizationResult', JSON.stringify(this.lastResult));
      } catch (error) {
        console.error('Error during optimization:', error)
        alert('Ошибка при оптимизации маршрутов: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.optimizing = false
      }
    },
    async resetRoutes() {
      if (!confirm('Вы уверены, что хотите сбросить все маршруты?')) {
        return
      }
      
      try {
        await axios.post(`${API_BASE_URL}/routes/reset`)
        this.lastResult = null
        localStorage.removeItem('lastOptimizationResult')
        await this.fetchStats()
      } catch (error) {
        console.error('Error resetting routes:', error)
        alert('Ошибка при сбросе маршрутов')
      }
    },
    toggleRoute(routeId) {
      if (this.expandedRoutes.includes(routeId)) {
        this.expandedRoutes = this.expandedRoutes.filter(id => id !== routeId)
      } else {
        this.expandedRoutes.push(routeId)
      }
    },
    getOrderDetails(orderId) {
      // Ищем заказ по ID в загруженных данных
      const order = this.orders.find(o => o.id === orderId)
      return order || null
    },
    expandAllRoutes() {
      this.expandedRoutes = this.lastResult.routes.map(route => route.id)
    },
    collapseAllRoutes() {
      this.expandedRoutes = []
    },
    getAlgorithmDisplayName(algorithm) {
      switch (algorithm) {
        case 'nearest_neighbor':
          return 'Ближайший сосед (быстрый)'
        case 'or_tools':
          return 'Google OR-Tools (точный)'
        case 'genetic':
          return 'Генетический алгоритм (эвристический)'
        default:
          return 'Неизвестный алгоритм'
      }
    }
  }
}
</script>

<style scoped>
.optimize-view {
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
}

.optimization-container {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.card {
  flex: 1;
  min-width: 400px;
}

.results-card {
  flex: 2;
  min-width: 500px;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.form-check {
  display: flex;
  align-items: center;
}

.form-check input {
  margin-right: 8px;
}

.algorithm-description {
  margin-top: 10px;
}

.desc-box {
  background-color: #f9f9f9;
  border-left: 3px solid #42b983;
  padding: 10px;
  font-size: 0.9rem;
}

.stats-box {
  background-color: #f9f9f9;
  border-radius: 4px;
  padding: 15px;
  margin-top: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: 500;
}

.genetic-settings {
  background-color: #f9f9f9;
  border-radius: 4px;
  padding: 15px;
  margin-top: 10px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
}

.loading-spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top: 4px solid #42b983;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-result {
  text-align: center;
  padding: 30px;
  color: #666;
}

.small {
  font-size: 0.9rem;
  color: #888;
  margin-top: 8px;
}

.result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  background-color: #f9f9f9;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  flex-direction: column;
}

.summary-item .label {
  font-size: 0.9rem;
  color: #666;
}

.summary-item .value {
  font-weight: 500;
  font-size: 1.1rem;
}

h4 {
  margin: 20px 0 15px 0;
}

.routes-accordion {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.route-accordion-item {
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}

.route-accordion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f9f9f9;
  padding: 10px 15px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.route-accordion-header:hover {
  background-color: #f0f0f0;
}

.route-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.route-title {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chevron-icon {
  font-size: 12px;
  transition: transform 0.2s ease;
  color: #666;
}

.chevron-icon.expanded {
  transform: rotate(180deg);
}

.route-metrics {
  display: flex;
  gap: 10px;
}

.route-accordion-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  background-color: #fafafa;
}

.route-accordion-content.expanded {
  max-height: 1000px;
  padding: 15px;
}

.route-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.depot-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.depot-marker {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #4a6cf7;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
}

.route-path {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 10px 0;
  padding-left: 20px;
  border-left: 2px solid #e0e0e0;
}

.route-step {
  display: flex;
  align-items: flex-start;
  padding: 8px 0;
  position: relative;
}

.route-step::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 12px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #f74a4a;
  border: 2px solid white;
  box-shadow: 0 0 0 2px #e0e0e0;
}

.step-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #f74a4a;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 11px;
  margin-right: 12px;
  flex-shrink: 0;
}

.step-info {
  flex: 1;
}

.order-info {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.order-details {
  font-size: 0.85rem;
  color: #666;
  display: flex;
  gap: 15px;
}

.order-details span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.depot-info.return {
  justify-content: center;
  margin-top: 10px;
  padding: 8px;
  background-color: #f0f0f0;
  border-radius: 6px;
}

.metric-badge {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.metric-badge.orders {
  background-color: #e8f5e8;
  color: #2e7d32;
}

.metric-badge.distance {
  background-color: #fff3e0;
  color: #f57c00;
}

.metric-badge.weight {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  align-self: flex-start;
}

.btn-primary:disabled {
  background-color: #a8e2cb;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #4a6cf7;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  display: inline-block;
}

.btn-outline {
  background-color: transparent;
  color: #ff4757;
  border: 1px solid #ff4757;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  width: 100%;
}

.routes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.routes-controls {
  display: flex;
  gap: 10px;
}

.btn-outline.small {
  padding: 6px 12px;
  font-size: 0.8rem;
}
</style> 