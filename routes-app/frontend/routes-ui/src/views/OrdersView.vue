<template>
  <div class="orders-view">
    <h2>Управление заказами</h2>
    
    <!-- Add order form -->
    <div class="card">
      <h3>Добавить новый заказ</h3>
      <div class="form-container">
        <div class="form-row">
          <div class="form-group">
            <label for="order-address">Адрес</label>
            <input type="text" id="order-address" v-model="newOrder.address" placeholder="Введите адрес доставки">
          </div>
          <div class="form-group">
            <label for="order-weight">Вес (кг)</label>
            <input type="number" id="order-weight" v-model.number="newOrder.weight" min="0.1" step="0.1">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="order-lat">Широта</label>
            <input type="number" id="order-lat" v-model.number="newOrder.latitude" step="0.000001">
          </div>
          <div class="form-group">
            <label for="order-lng">Долгота</label>
            <input type="number" id="order-lng" v-model.number="newOrder.longitude" step="0.000001">
          </div>
        </div>
        <button @click="addOrder" class="btn-primary">Добавить заказ</button>
      </div>
    </div>
    
    <!-- Orders list -->
    <div class="card">
      <h3>Список заказов</h3>
      <div class="filter-controls">
        <button @click="fetchOrders()" class="btn-outline">Все заказы</button>
        <button @click="fetchOrders('unassigned')" class="btn-outline">Без маршрута</button>
        <button @click="fetchOrders('assigned')" class="btn-outline">Распределенные</button>
      </div>
      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="orders.length === 0" class="empty-state">
        Нет заказов
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Адрес</th>
            <th>Вес (кг)</th>
            <th>Координаты</th>
            <th>Маршрут</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.id">
            <td>{{ order.id }}</td>
            <td>{{ order.location ? order.location.address : '-' }}</td>
            <td>{{ order.weight }}</td>
            <td>{{ order.location ? `${order.location.latitude}, ${order.location.longitude}` : '-' }}</td>
            <td>{{ order.courier_id ? `Курьер #${order.courier_id}` : 'Не распределен' }}</td>
            <td>
              <button @click="deleteOrder(order.id)" class="btn-danger">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <span>Показано {{ orders.length }} из {{ totalOrders }} заказов</span>
        <button v-if="currentPage > 1" @click="previousPage" class="btn-outline">← Предыдущая</button>
        <button v-if="hasMoreOrders" @click="nextPage" class="btn-outline">Следующая →</button>
      </div>
    </div>
    
    <!-- Bulk actions -->
    <div class="card">
      <h3>Массовые действия</h3>
      <div class="bulk-actions">
        <button @click="generateRandomOrders" class="btn-secondary">Сгенерировать тестовые заказы</button>
        <button @click="deleteAllOrders" class="btn-danger">Удалить все заказы</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { API_BASE_URL } from '../config'

export default {
  name: 'OrdersView',
  data() {
    return {
      orders: [],
      loading: true,
      currentPage: 1,
      pageSize: 20,
      totalOrders: 0,
      hasMoreOrders: false,
      filterType: '',
      newOrder: {
        address: '',
        weight: 1.0,
        latitude: 55.7558,
        longitude: 37.6173
      }
    }
  },
  mounted() {
    this.fetchOrders()
  },
  methods: {
    async fetchOrders(filterType = '') {
      this.loading = true
      this.filterType = filterType
      
      try {
        let url = `${API_BASE_URL}/orders?skip=${(this.currentPage - 1) * this.pageSize}&limit=${this.pageSize}`
        
        // Add filter if specified
        if (filterType === 'unassigned') {
          url += '&assigned=false'
        } else if (filterType === 'assigned') {
          url += '&assigned=true'
        }
        
        const response = await axios.get(url)
        this.orders = response.data
        
        // Get total count for pagination
        const countResponse = await axios.get(`${API_BASE_URL}/orders/count`)
        this.totalOrders = countResponse.data.count
        
        // Check if there are more orders
        this.hasMoreOrders = this.currentPage * this.pageSize < this.totalOrders
      } catch (error) {
        console.error('Error fetching orders:', error)
      } finally {
        this.loading = false
      }
    },
    async addOrder() {
      try {
        // Validate inputs
        if (!this.newOrder.address) {
          alert('Пожалуйста, заполните адрес')
          return
        }

        // Подготовка данных в формате, ожидаемом API
        const order = {
          customer_name: "Клиент",
          customer_phone: "+7-000-000-0000",
          weight: parseFloat(this.newOrder.weight),
          items_count: 1,
          location: {
            latitude: parseFloat(this.newOrder.latitude),
            longitude: parseFloat(this.newOrder.longitude),
            address: this.newOrder.address
          }
        }

        const response = await axios.post(`${API_BASE_URL}/orders`, order)
        
        // Add to the beginning of the list if we're on the first page
        if (this.currentPage === 1) {
          this.orders.unshift(response.data)
          if (this.orders.length > this.pageSize) {
            this.orders.pop()
          }
        }
        
        // Increment total count
        this.totalOrders++
        
        // Reset form
        this.newOrder = {
          address: '',
          weight: 1.0,
          latitude: 55.7558,
          longitude: 37.6173
        }
      } catch (error) {
        console.error('Error adding order:', error)
        alert('Ошибка при добавлении заказа')
      }
    },
    async deleteOrder(id) {
      if (!confirm('Вы уверены, что хотите удалить этот заказ?')) {
        return
      }
      
      try {
        await axios.delete(`${API_BASE_URL}/orders/${id}`)
        this.orders = this.orders.filter(order => order.id !== id)
        this.totalOrders--
      } catch (error) {
        console.error('Error deleting order:', error)
        alert('Ошибка при удалении заказа')
      }
    },
    nextPage() {
      this.currentPage++
      this.fetchOrders(this.filterType)
    },
    previousPage() {
      if (this.currentPage > 1) {
        this.currentPage--
        this.fetchOrders(this.filterType)
      }
    },
    async generateRandomOrders() {
      const count = prompt('Сколько случайных заказов сгенерировать?', '10')
      if (!count) return
      
      const numOrders = parseInt(count)
      if (isNaN(numOrders) || numOrders <= 0) {
        alert('Пожалуйста, введите положительное число')
        return
      }
      
      try {
        this.loading = true
        
        // Generate random orders within Moscow area
        const mockOrders = []
        for (let i = 0; i < numOrders; i++) {
          // Random locations within Moscow area
          const latitude = 55.7558 + (Math.random() - 0.5) * 0.1
          const longitude = 37.6173 + (Math.random() - 0.5) * 0.1
          
          mockOrders.push({
            customer_name: `Клиент ${i + 1}`,
            customer_phone: `+7-${Math.floor(Math.random() * 900) + 100}-${Math.floor(Math.random() * 900) + 100}-${Math.floor(Math.random() * 9000) + 1000}`,
            weight: +(Math.random() * 9.9 + 0.1).toFixed(1), // Random weight between 0.1 and 10
            items_count: Math.floor(Math.random() * 5) + 1, // Random item count between 1 and 5
            location: {
              latitude: latitude,
              longitude: longitude,
              address: `Тестовый адрес ${i + 1}`
            }
          })
        }
        
        // Use the bulk create endpoint
        await axios.post(`${API_BASE_URL}/orders/bulk`, { orders: mockOrders })
        
        // Refresh orders list
        this.currentPage = 1
        this.fetchOrders(this.filterType)
      } catch (error) {
        console.error('Error generating random orders:', error)
        alert('Ошибка при генерации заказов')
      } finally {
        this.loading = false
      }
    },
    async deleteAllOrders() {
      if (!confirm('Вы уверены, что хотите удалить ВСЕ заказы? Это действие нельзя отменить.')) {
        return
      }
      
      try {
        this.loading = true
        await axios.delete(`${API_BASE_URL}/orders`)
        this.orders = []
        this.totalOrders = 0
        this.currentPage = 1
      } catch (error) {
        console.error('Error deleting all orders:', error)
        alert('Ошибка при удалении всех заказов')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.orders-view {
  max-width: 900px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
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

.filter-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
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

.btn-outline {
  background-color: transparent;
  color: #42b983;
  border: 1px solid #42b983;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  background-color: #4a6cf7;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-danger {
  background-color: #ff4757;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: #666;
}

.loading {
  padding: 20px;
  text-align: center;
  color: #666;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.bulk-actions {
  display: flex;
  gap: 16px;
}
</style> 