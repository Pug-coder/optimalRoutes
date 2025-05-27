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
          <div class="address-input-group">
            <input 
              type="text" 
              id="depot-address" 
              v-model="newDepot.address" 
              placeholder="Введите адрес склада"
              @input="onAddressChange"
            >
            <button 
              @click="geocodeAddress" 
              class="btn-geocode"
              :disabled="!newDepot.address || geocoding"
              title="Получить координаты по адресу"
            >
              {{ geocoding ? '...' : '📍' }}
            </button>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="depot-lat">Широта:</label>
            <input type="number" id="depot-lat" v-model.number="newDepot.latitude" step="0.000001">
          </div>
          <div class="form-group">
            <label for="depot-lng">Долгота:</label>
            <input type="number" id="depot-lng" v-model.number="newDepot.longitude" step="0.000001">
          </div>
        </div>
        <div class="form-actions">
          <button @click="addDepotWithAddress" class="btn-primary">
            Добавить склад (автогеокодирование)
          </button>
          <button @click="addDepot" class="btn-secondary">
            Добавить склад (с координатами)
          </button>
        </div>
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
            <td>{{ depot.location ? `${depot.location.latitude}, ${depot.location.longitude}` : '-' }}</td>
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
        latitude: 55.7558,
        longitude: 37.6173
      },
      geocoding: false
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
            latitude: this.newDepot.latitude,
            longitude: this.newDepot.longitude,
            address: this.newDepot.address
          }
        }

        const response = await axios.post(`${API_BASE_URL}/depots`, depotData)
        this.depots.push(response.data)
        
        // Reset form
        this.newDepot = {
          name: '',
          address: '',
          latitude: 55.7558,
          longitude: 37.6173
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
    },
    async geocodeAddress() {
      this.geocoding = true
      try {
        const response = await axios.post(`${API_BASE_URL}/geocoding/geocode`, {
          address: this.newDepot.address
        })
        if (response.data.found) {
          this.newDepot.latitude = response.data.latitude
          this.newDepot.longitude = response.data.longitude
        } else {
          alert('Не удалось найти координаты для указанного адреса')
        }
      } catch (error) {
        console.error('Error geocoding address:', error)
        alert('Ошибка при получении координат')
      } finally {
        this.geocoding = false
      }
    },
    onAddressChange() {
      // Reset latitude and longitude when address changes
      this.newDepot.latitude = null
      this.newDepot.longitude = null
    },
    async addDepotWithAddress() {
      try {
        // Validate inputs
        if (!this.newDepot.name || !this.newDepot.address) {
          alert('Пожалуйста, заполните название и адрес')
          return
        }

        // Подготовка данных для API с автогеокодированием
        const depotData = {
          name: this.newDepot.name,
          address: this.newDepot.address
        }

        const response = await axios.post(`${API_BASE_URL}/depots/with-address`, depotData)
        this.depots.push(response.data)
        
        // Reset form
        this.newDepot = {
          name: '',
          address: '',
          latitude: 55.7558,
          longitude: 37.6173
        }
      } catch (error) {
        console.error('Error adding depot with address:', error)
        alert('Ошибка при добавлении склада с автоматическим геокодированием')
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

.address-input-group {
  position: relative;
}

.btn-geocode {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background-color: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  margin: 0;
  font-size: 16px;
}

.btn-geocode:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-primary {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  background-color: #6c757d;
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
</style> 