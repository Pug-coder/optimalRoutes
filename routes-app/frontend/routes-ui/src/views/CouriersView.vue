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
            <select id="courier-depot-id" v-model="newCourier.depot_id">
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
            <td>{{ courier.max_weight || '-' }} кг</td>
            <td>{{ courier.max_distance === 'Infinity' ? 'Без ограничений' : `${courier.max_distance} км` }}</td>
            <td>
              <button @click="editCourier(courier)" class="btn-secondary">Редактировать</button>
              <button @click="deleteCourier(courier.id)" class="btn-danger">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Edit courier modal -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>Редактировать курьера</h3>
          <button @click="closeEditModal" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-container">
            <div class="form-group">
              <label for="edit-courier-name">Имя</label>
              <input type="text" id="edit-courier-name" v-model="editingCourier.name" placeholder="Введите имя курьера">
            </div>
            <div class="form-group">
              <label for="edit-courier-phone">Телефон</label>
              <input type="text" id="edit-courier-phone" v-model="editingCourier.phone" placeholder="Введите телефон">
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="edit-courier-max-capacity">Макс. заказов</label>
                <input type="number" id="edit-courier-max-capacity" v-model.number="editingCourier.max_capacity" min="1" step="1">
              </div>
              <div class="form-group">
                <label for="edit-courier-max-weight">Макс. вес (кг)</label>
                <input type="number" id="edit-courier-max-weight" v-model.number="editingCourier.max_weight" min="0.1" step="0.1">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="edit-courier-max-distance">Макс. расстояние (км)</label>
                <input type="number" id="edit-courier-max-distance" v-model.number="editingCourier.max_distance" min="1" step="1">
              </div>
              <div class="form-group">
                <label for="edit-courier-depot-id">Склад</label>
                <select id="edit-courier-depot-id" v-model="editingCourier.depot_id">
                  <option disabled value="">Выберите склад</option>
                  <option v-for="depot in depots" :key="depot.id" :value="depot.id">
                    {{ depot.name }}
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeEditModal" class="btn-secondary">Отмена</button>
          <button @click="updateCourier" class="btn-primary">Сохранить</button>
        </div>
      </div>
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
      showEditModal: false,
      editingCourier: {
        id: null,
        name: '',
        phone: '',
        max_capacity: 5,
        max_distance: 50,
        depot_id: ''
      },
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
        
        console.log('Fetched depots:', this.depots)
        console.log('First depot id type:', this.depots.length > 0 ? typeof this.depots[0].id : 'no depots')
        
        // Set default depot if there are any
        if (this.depots.length > 0 && !this.newCourier.depot_id) {
          this.newCourier.depot_id = this.depots[0].id
          console.log('Set default depot_id:', this.newCourier.depot_id, 'type:', typeof this.newCourier.depot_id)
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
          max_weight: parseFloat(this.newCourier.max_weight),
          max_distance: parseFloat(this.newCourier.max_distance)
        }

        console.log('Adding courier with data:', courier)
        console.log('depot_id type:', typeof courier.depot_id)

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
        console.error('Error response:', error.response?.data)
        if (error.response && error.response.data && error.response.data.detail) {
          alert(`Ошибка при добавлении курьера: ${error.response.data.detail}`)
        } else {
          alert('Ошибка при добавлении курьера')
        }
      }
    },
    editCourier(courier) {
      this.editingCourier = {
        id: courier.id,
        name: courier.name,
        phone: courier.phone || '',
        max_capacity: courier.max_capacity,
        max_weight: courier.max_weight || 20,
        max_distance: courier.max_distance,
        depot_id: courier.depot_id
      }
      this.showEditModal = true
    },
    closeEditModal() {
      this.showEditModal = false
      this.editingCourier = {
        id: null,
        name: '',
        phone: '',
        max_capacity: 5,
        max_weight: 20,
        max_distance: 50,
        depot_id: ''
      }
    },
    async updateCourier() {
      try {
        // Validate inputs
        if (!this.editingCourier.name || !this.editingCourier.depot_id) {
          alert('Пожалуйста, заполните все обязательные поля')
          return
        }

        // Подготовка данных для PATCH запроса - отправляем только заполненные поля
        const updateData = {}
        
        if (this.editingCourier.name && this.editingCourier.name.trim()) {
          updateData.name = this.editingCourier.name.trim()
        }
        
        if (this.editingCourier.phone && this.editingCourier.phone.trim()) {
          updateData.phone = this.editingCourier.phone.trim()
        }
        
        if (this.editingCourier.max_capacity) {
          updateData.max_capacity = parseInt(this.editingCourier.max_capacity)
        }
        
        if (this.editingCourier.max_weight) {
          updateData.max_weight = parseFloat(this.editingCourier.max_weight)
        }
        
        if (this.editingCourier.max_distance) {
          updateData.max_distance = parseFloat(this.editingCourier.max_distance)
        }
        
        if (this.editingCourier.depot_id) {
          updateData.depot_id = this.editingCourier.depot_id
        }

        console.log('Sending PATCH request with data:', updateData)
        console.log('Courier ID:', this.editingCourier.id)

        const response = await axios.patch(`${API_BASE_URL}/couriers/${this.editingCourier.id}`, updateData)
        
        // Обновляем курьера в списке
        const index = this.couriers.findIndex(c => c.id === this.editingCourier.id)
        if (index !== -1) {
          this.couriers[index] = response.data
        }
        
        this.closeEditModal()
        alert('Курьер успешно обновлен')
      } catch (error) {
        console.error('Error updating courier:', error)
        console.error('Error response:', error.response?.data)
        if (error.response && error.response.data && error.response.data.detail) {
          alert(`Ошибка при обновлении курьера: ${error.response.data.detail}`)
        } else {
          alert('Ошибка при обновлении курьера')
        }
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
        if (error.response && error.response.data && error.response.data.detail) {
          alert(`Ошибка при удалении курьера: ${error.response.data.detail}`)
        } else {
          alert('Ошибка при удалении курьера')
        }
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

.btn-secondary {
  background-color: #6c757d;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-right: 8px;
}

.btn-danger {
  background-color: #ff4757;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-left: 8px;
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

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 20px;
  border-top: 1px solid #eee;
}
</style> 