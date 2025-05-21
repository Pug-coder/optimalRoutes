<template>
  <div class="depots-view">
    <h2>Управление складами</h2>
    
    <!-- Add depot form -->
    <div class="card">
      <h3>Добавить новый склад</h3>
      <div class="form-container">
        <div class="form-group">
          <label for="depot-name">Название</label>
          <input type="text" id="depot-name" v-model="newDepot.name" placeholder="Введите название склада">
        </div>
        <div class="form-group">
          <label for="depot-address">Адрес</label>
          <input type="text" id="depot-address" v-model="newDepot.address" placeholder="Введите адрес склада">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="depot-lat">Широта</label>
            <input type="number" id="depot-lat" v-model.number="newDepot.lat" step="0.000001">
          </div>
          <div class="form-group">
            <label for="depot-lng">Долгота</label>
            <input type="number" id="depot-lng" v-model.number="newDepot.lng" step="0.000001">
          </div>
        </div>
        <button @click="addDepot" class="btn-primary">Добавить склад</button>
      </div>
    </div>
    
    <!-- Depots list -->
    <div class="card">
      <h3>Список складов</h3>
      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="depots.length === 0" class="empty-state">
        Нет добавленных складов
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Адрес</th>
            <th>Координаты</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="depot in depots" :key="depot.id">
            <td>{{ depot.id }}</td>
            <td>{{ depot.name }}</td>
            <td>{{ depot.location ? depot.location.address : '-' }}</td>
            <td>{{ depot.location ? `${depot.location.lat}, ${depot.location.lng}` : '-' }}</td>
            <td>
              <button @click="deleteDepot(depot.id)" class="btn-danger">Удалить</button>
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
  name: 'DepotsView',
  data() {
    return {
      depots: [],
      loading: true,
      newDepot: {
        name: '',
        address: '',
        lat: 55.7558,
        lng: 37.6173
      }
    }
  },
  mounted() {
    this.fetchDepots()
  },
  methods: {
    async fetchDepots() {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE_URL}/depots`)
        this.depots = response.data
      } catch (error) {
        console.error('Error fetching depots:', error)
      } finally {
        this.loading = false
      }
    },
    async addDepot() {
      try {
        // Validate inputs
        if (!this.newDepot.name || !this.newDepot.address) {
          alert('Пожалуйста, заполните все поля')
          return
        }

        // Подготовка данных в формате, ожидаемом API
        const depotData = {
          name: this.newDepot.name,
          location: {
            lat: this.newDepot.lat,
            lng: this.newDepot.lng,
            address: this.newDepot.address
          }
        }

        const response = await axios.post(`${API_BASE_URL}/depots`, depotData)
        this.depots.push(response.data)
        
        // Reset form
        this.newDepot = {
          name: '',
          address: '',
          lat: 55.7558,
          lng: 37.6173
        }
      } catch (error) {
        console.error('Error adding depot:', error)
        alert('Ошибка при добавлении склада')
      }
    },
    async deleteDepot(id) {
      if (!confirm('Вы уверены, что хотите удалить этот склад?')) {
        return
      }
      
      try {
        await axios.delete(`${API_BASE_URL}/depots/${id}`)
        this.depots = this.depots.filter(depot => depot.id !== id)
      } catch (error) {
        console.error('Error deleting depot:', error)
        alert('Ошибка при удалении склада')
      }
    }
  }
}
</script>

<style scoped>
.depots-view {
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
</style> 