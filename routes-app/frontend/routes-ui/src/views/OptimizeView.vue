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
              <option value="ortools">Google OR-Tools (точный)</option>
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
            <div v-if="settings.algorithm === 'ortools'" class="desc-box">
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
              <span class="value">{{ lastResult.algorithm === 'ortools' ? 'Google OR-Tools' : 'Генетический алгоритм' }}</span>
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
          
          <h4>Созданные маршруты</h4>
          <div class="routes-list">
            <div v-for="route in lastResult.routes" :key="route.id" class="route-item">
              <div class="route-header">
                <div class="route-title">
                  Маршрут #{{ route.id }} (Курьер: {{ getCourierName(route.courier_id) }})
                </div>
                <div class="route-metrics">
                  <span>{{ route.points.length }} заказов</span>
                  <span>{{ route.total_distance.toFixed(2) }} км</span>
                </div>
              </div>
              <div class="route-points">
                <div v-for="(point, index) in route.points" :key="index" class="route-point">
                  <div class="point-marker">
                    O
                  </div>
                  <div class="point-info">
                    Заказ #{{ point.order_id }}
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
        algorithm: 'ortools',
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
      couriers: []
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
        
        // Fetch order counts
        const ordersCountResponse = await axios.get(`${API_BASE_URL}/orders/count`)
        this.stats.orderCount = ordersCountResponse.data.count
        
        // Fetch unassigned order count
        const unassignedResponse = await axios.get(`${API_BASE_URL}/orders/count?assigned=false`)
        this.stats.unassignedCount = unassignedResponse.data.count
        
        // Fetch latest optimization result
        const routesResponse = await axios.get(`${API_BASE_URL}/routes`)
        if (routesResponse.data && routesResponse.data.length > 0) {
          // Mock a result object since we don't store the full optimization result
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
    async runOptimization() {
      if (this.optimizing) return
      
      try {
        this.optimizing = true
        
        // Reset routes if needed
        if (this.settings.resetPrevious) {
          await axios.post(`${API_BASE_URL}/routes/reset`)
        }
        
        // Prepare optimization parameters
        let optimizeEndpoint = '/routes/optimize';
        let params = {};
        
        if (this.settings.algorithm === 'genetic') {
          optimizeEndpoint = '/routes/optimize/genetic';
          params = {
            population_size: this.settings.genetic.population_size,
            generations: this.settings.genetic.generations,
            mutation_rate: this.settings.genetic.mutation_rate,
            elite_size: this.settings.genetic.elite_size
          };
        }
        
        // Run optimization
        const response = await axios.post(`${API_BASE_URL}${optimizeEndpoint}`, params)
        this.lastResult = response.data
        
        // Refresh stats
        await this.fetchStats()
      } catch (error) {
        console.error('Error during optimization:', error)
        alert('Ошибка при оптимизации маршрутов')
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
        await this.fetchStats()
      } catch (error) {
        console.error('Error resetting routes:', error)
        alert('Ошибка при сбросе маршрутов')
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

.routes-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: 500px;
  overflow-y: auto;
}

.route-item {
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}

.route-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f9f9f9;
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
}

.route-title {
  font-weight: 500;
}

.route-metrics {
  display: flex;
  gap: 15px;
  font-size: 0.9rem;
  color: #666;
}

.route-points {
  padding: 10px 15px;
}

.route-point {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.route-point:last-child {
  border-bottom: none;
}

.point-marker {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #f74a4a;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 10px;
}

.point-info {
  font-size: 0.9rem;
  color: #666;
}

.point-marker.depot {
  background-color: #4a6cf7;
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
</style> 