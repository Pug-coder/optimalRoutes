<template>
  <div class="couriers-view">
    <h2>Управление курьерами</h2>
    
    <!-- Add courier form -->
    <div class="card">
      <h3>Добавить нового курьера</h3>
      <div class="form-container">
        <div class="form-group">
          <label for="courier-name">Имя</label>
          <input type="text" id="courier-name" v-model="newCourier.name" placeholder="Введите имя курьера">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="courier-max-orders">Макс. заказов</label>
            <input type="number" id="courier-max-orders" v-model.number="newCourier.max_orders" min="1" step="1">
          </div>
          <div class="form-group">
            <label for="courier-max-weight">Макс. вес (кг)</label>
            <input type="number" id="courier-max-weight" v-model.number="newCourier.max_weight" min="0.1" step="0.1">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="courier-max-distance">Макс. расстояние (км)</label>
            <input type="number" id="courier-max-distance" v-model.number="newCourier.max_distance" min="1" step="1">
          </div>
          <div class="form-group">
            <label for="courier-depot-id">Склад</label>
            <select id="courier-depot-id" v-model.number="newCourier.depot_id">
              <option disabled value="">Выберите склад</option>
              <option v-for="depot in depots" :key="depot.id" :value="depot.id">
                {{ depot.name }}
              </option>
            </select>
          </div>
        </div>
        <button @click="addCourier" class="btn-primary">Добавить курьера</button>
      </div>
    </div>
    
    <!-- Couriers list -->
    <div class="card">
      <h3>Список курьеров</h3>
      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="couriers.length === 0" class="empty-state">
        Нет добавленных курьеров
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Склад</th>
            <th>Макс. заказов</th>
            <th>Макс. вес</th>
            <th>Макс. расстояние</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="courier in couriers" :key="courier.id">
            <td>{{ courier.id }}</td>
            <td>{{ courier.name }}</td>
            <td>{{ getDepotName(courier.depot_id) }}</td>
            <td>{{ courier.max_capacity || '-' }}</td>
            <td>{{ 20 }} кг</td>
            <td>{{ courier.max_distance === 'Infinity' ? 'Без ограничений' : `${courier.max_distance} км` }}</td>
            <td>
              <button @click="deleteCourier(courier.id)" class="btn-danger">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { API_BASE_URL } from '../config'

export default {
  name: 'CouriersView',
  data() {
    return {
      couriers: [],
      depots: [],
      loading: true,
      newCourier: {
        name: '',
        max_orders: 5,
        max_weight: 20,
        max_distance: 50,
        depot_id: ''
      }
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        // Fetch depots first
        const depotsResponse = await axios.get(`${API_BASE_URL}/depots`)
        this.depots = depotsResponse.data
        
        // Set default depot if there are any
        if (this.depots.length > 0 && !this.newCourier.depot_id) {
          this.newCourier.depot_id = this.depots[0].id
        }
        
        // Fetch couriers
        const couriersResponse = await axios.get(`${API_BASE_URL}/couriers`)
        this.couriers = couriersResponse.data
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        this.loading = false
      }
    },
    getDepotName(depotId) {
      const depot = this.depots.find(d => d.id === depotId)
      return depot ? depot.name : 'Неизвестно'
    },
    async addCourier() {
      try {
        // Validate inputs
        if (!this.newCourier.name || !this.newCourier.depot_id) {
          alert('Пожалуйста, заполните все поля')
          return
        }

        // Подготовка данных в формате, ожидаемом API
        const courier = {
          name: this.newCourier.name,
          phone: "+7-000-000-0000",
          depot_id: this.newCourier.depot_id,
          max_capacity: parseInt(this.newCourier.max_orders),
          max_distance: parseFloat(this.newCourier.max_distance)
        }

        const response = await axios.post(`${API_BASE_URL}/couriers`, courier)
        this.couriers.push(response.data)
        
        // Reset form
        this.newCourier = {
          name: '',
          max_orders: 5,
          max_weight: 20,
          max_distance: 50,
          depot_id: this.depots.length > 0 ? this.depots[0].id : ''
        }
      } catch (error) {
        console.error('Error adding courier:', error)
        alert('Ошибка при добавлении курьера')
      }
    },
    async deleteCourier(id) {
      if (!confirm('Вы уверены, что хотите удалить этого курьера?')) {
        return
      }
      
      try {
        await axios.delete(`${API_BASE_URL}/couriers/${id}`)
        this.couriers = this.couriers.filter(courier => courier.id !== id)
      } catch (error) {
        console.error('Error deleting courier:', error)
        alert('Ошибка при удалении курьера')
      }
    }
  }
}
</script>

<style scoped>
.couriers-view {
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

select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  width: 100%;
}
</style> 