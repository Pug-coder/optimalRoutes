<template>
  <div class="map-view">
    <div class="map-container">
      <h2>Карта маршрутов</h2>
      <div class="search-container">
        <input 
          type="text" 
          v-model="searchAddress" 
          placeholder="Введите адрес для поиска" 
          class="search-input"
          @keyup.enter="searchLocation"
        />
        <button @click="searchLocation" class="search-button">Найти</button>
      </div>
      <div id="map" class="leaflet-map"></div>
    </div>
    <div class="map-controls">
      <div class="card">
        <h3>Слои карты</h3>
        <div class="map-layers">
          <div class="form-group">
            <input type="checkbox" id="depots-layer" v-model="showDepots">
            <label for="depots-layer">Показать склады</label>
          </div>
          <div class="form-group">
            <input type="checkbox" id="orders-layer" v-model="showOrders">
            <label for="orders-layer">Показать заказы</label>
          </div>
          <div class="form-group">
            <input type="checkbox" id="routes-layer" v-model="showRoutes">
            <label for="routes-layer">Показать маршруты</label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import L from 'leaflet'
import axios from 'axios'
import { API_BASE_URL } from '../config'
import 'leaflet.polyline.snakeanim/L.Polyline.SnakeAnim.js'

// Добавляем функцию для декодирования полилиний в формате Google (polyline)
L.Polyline.fromEncoded = function(encoded, options) {
  var points = [];
  var index = 0, len = encoded.length;
  var lat = 0, lng = 0;

  while (index < len) {
    var b, shift = 0, result = 0;
    do {
      b = encoded.charAt(index++).charCodeAt(0) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    var dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charAt(index++).charCodeAt(0) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    var dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lng += dlng;

    points.push(L.latLng([lat * 1e-5, lng * 1e-5]));
  }

  return L.polyline(points, options || {});
};

// Добавляем константу для OSRM API
const OSRM_API_URL = 'https://router.project-osrm.org/route/v1/driving/';

// Fix for Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png')
})

export default {
  name: 'MapView',
  data() {
    return {
      map: null,
      depots: [],
      orders: [],
      couriers: [],
      routes: [],
      showDepots: true,
      showOrders: true,
      showRoutes: true,
      depotMarkers: L.layerGroup(),
      orderMarkers: L.layerGroup(),
      routeLines: L.layerGroup(),
      searchAddress: '',
      searchMarker: null
    }
  },
  mounted() {
    this.initMap()
    this.fetchData()
  },
  watch: {
    showDepots(val) {
      if (val) {
        this.depotMarkers.addTo(this.map)
      } else {
        this.depotMarkers.removeFrom(this.map)
      }
    },
    showOrders(val) {
      if (val) {
        this.orderMarkers.addTo(this.map)
      } else {
        this.orderMarkers.removeFrom(this.map)
      }
    },
    showRoutes(val) {
      if (val) {
        this.routeLines.addTo(this.map)
      } else {
        this.routeLines.removeFrom(this.map)
      }
    }
  },
  methods: {
    initMap() {
      this.map = L.map('map').setView([55.7558, 37.6173], 10) // Default view on Moscow

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(this.map)

      this.depotMarkers.addTo(this.map)
      this.orderMarkers.addTo(this.map)
      this.routeLines.addTo(this.map)
    },
    async fetchData() {
      try {
        const depotsResponse = await axios.get(`${API_BASE_URL}/depots`)
        this.depots = depotsResponse.data
        this.renderDepots()

        const ordersResponse = await axios.get(`${API_BASE_URL}/orders`)
        this.orders = ordersResponse.data
        this.renderOrders()

        const routesResponse = await axios.get(`${API_BASE_URL}/routes`)
        this.routes = routesResponse.data
        this.renderRoutes()
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    },
    renderDepots() {
      this.depotMarkers.clearLayers()
      
      this.depots.forEach(depot => {
        if (depot.location) {
          const marker = L.marker([depot.location.lat, depot.location.lng], {
            icon: L.divIcon({
              className: 'depot-marker',
              html: `<div class="depot-icon">D</div>`,
              iconSize: [24, 24]
            })
          })
          
          marker.bindPopup(`
            <strong>Склад: ${depot.name}</strong><br>
            Адрес: ${depot.location.address || 'Нет адреса'}
          `)
          
          this.depotMarkers.addLayer(marker)
        }
      })
    },
    renderOrders() {
      this.orderMarkers.clearLayers()
      
      this.orders.forEach(order => {
        if (order.location) {
          // Определяем цвет маркера в зависимости от статуса заказа
          const markerColor = order.status === 'assigned' ? '#4a6cf7' : '#f74a4a';
          
          const marker = L.marker([order.location.lat, order.location.lng], {
            icon: L.divIcon({
              className: 'order-marker',
              html: `<div class="order-icon" style="background-color: ${markerColor};">O</div>`,
              iconSize: [24, 24]
            })
          })
          
          // Получаем информацию о курьере, если заказ назначен
          let courierInfo = '';
          if (order.courier_id) {
            const courier = this.couriers.find(c => c.id === order.courier_id);
            courierInfo = courier ? 
              `<br>Курьер: ${courier.name || 'Неизвестно'}` : 
              `<br>Курьер: ID ${order.courier_id}`;
          }
          
          marker.bindPopup(`
            <strong>Заказ #${order.id}</strong><br>
            Клиент: ${order.customer_name || 'Нет имени'}<br>
            Адрес: ${order.location.address || 'Нет адреса'}<br>
            Вес: ${order.weight} кг${courierInfo}
            <br>Статус: ${order.status === 'assigned' ? 'Назначен' : 'Ожидает назначения'}
          `)
          
          this.orderMarkers.addLayer(marker)
        }
      })
    },
    async renderRoutes() {
      this.routeLines.clearLayers()
      
      // Generate different colors for each route
      const getRouteColor = (index) => {
        const colors = ['#FF5733', '#33FF57', '#3357FF', '#F033FF', '#FF33A8', '#33FFF5', '#FFD433']
        return colors[index % colors.length]
      }
      
      if (this.routes && this.routes.length) {
        for (const [index, route] of this.routes.entries()) {
          if (route.points && route.points.length > 0) {
            // Собираем точки маршрута, находя координаты заказов и склада
            const depot = this.depots.find(d => d.id === route.depot_id);
            if (!depot || !depot.location) continue;
            
            // Точки маршрута - склад в начале, затем заказы, затем возврат на склад
            const routePoints = [];
            
            // Добавляем склад в начало маршрута
            routePoints.push([depot.location.lat, depot.location.lng]);
            
            // Добавляем заказы
            for (const point of route.points) {
              const order = this.orders.find(o => o.id === point.order_id);
              if (order && order.location) {
                routePoints.push([order.location.lat, order.location.lng]);
              }
            }
            
            // Добавляем склад в конец маршрута
            routePoints.push([depot.location.lat, depot.location.lng]);
            
            if (routePoints.length > 1) {
              // Получаем маршрут по дорогам
              try {
                // Разбиваем на сегменты, чтобы избежать ограничений API
                const segments = [];
                for (let i = 0; i < routePoints.length - 1; i++) {
                  segments.push([routePoints[i], routePoints[i + 1]]);
                }
                
                // Добавляем маркеры начала и конца маршрута
                const startMarker = L.marker(routePoints[0], {
                  icon: L.divIcon({
                    className: 'start-marker',
                    html: `<div style="width: 15px; height: 15px;"></div>`,
                    iconSize: [15, 15]
                  }),
                  title: 'Старт'
                });
                
                const endMarker = L.marker(routePoints[routePoints.length - 1], {
                  icon: L.divIcon({
                    className: 'end-marker',
                    html: `<div style="width: 15px; height: 15px;"></div>`,
                    iconSize: [15, 15]
                  }),
                  title: 'Финиш'
                });
                
                startMarker.bindPopup(`<strong>Начало маршрута</strong><br>Склад: ${depot.name}`);
                endMarker.bindPopup(`<strong>Конец маршрута</strong><br>Склад: ${depot.name}`);
                
                this.routeLines.addLayer(startMarker);
                this.routeLines.addLayer(endMarker);
                
                // Создаем маршрут по дорогам для каждого сегмента
                for (const segment of segments) {
                  const roadPoints = await this.getRouteByRoad(segment);
                  const routeLine = L.polyline(roadPoints, {
                    color: getRouteColor(index),
                    weight: 4,
                    opacity: 0.7
                  });
                  
                  routeLine.bindPopup(`
                    <strong>Маршрут #${route.id}</strong><br>
                    Курьер: ${route.courier_id}<br>
                    Кол-во заказов: ${route.points.length}<br>
                    Дистанция: ${route.total_distance.toFixed(2)} км
                  `);
                  
                  this.routeLines.addLayer(routeLine);
                  
                  // Добавляем анимацию
                  setTimeout(() => {
                    try {
                      routeLine.snakeIn();
                    } catch (e) {
                      console.error('Animation error:', e);
                    }
                  }, 100 * index);
                }
              } catch (error) {
                console.error('Error rendering route by road:', error);
                
                // Если не удалось получить маршрут по дорогам, рисуем прямыми линиями
                const routeLine = L.polyline(routePoints, {
                  color: getRouteColor(index),
                  weight: 3,
                  opacity: 0.7,
                  dashArray: '5, 10' // пунктирная линия для обозначения "воздушного" маршрута
                });
                
                routeLine.bindPopup(`
                  <strong>Маршрут #${route.id}</strong><br>
                  Курьер: ${route.courier_id}<br>
                  Кол-во заказов: ${route.points.length}<br>
                  Дистанция: ${route.total_distance.toFixed(2)} км
                `);
                
                this.routeLines.addLayer(routeLine);
                
                // Добавляем анимацию для прямых линий тоже
                setTimeout(() => {
                  try {
                    routeLine.snakeIn();
                  } catch (e) {
                    console.error('Animation error:', e);
                  }
                }, 100 * index);
              }
            }
          }
        }
      }
    },
    // Получение маршрута по реальным дорогам
    async getRouteByRoad(points) {
      if (points.length < 2) return [];
      
      try {
        // Формируем строку координат для OSRM API
        const coordinates = points.map(point => `${point[1]},${point[0]}`).join(';');
        const response = await axios.get(`${OSRM_API_URL}${coordinates}?overview=full&geometries=polyline`);
        
        if (response.data.code !== 'Ok' || !response.data.routes || !response.data.routes.length) {
          console.error('OSRM error:', response.data);
          return points; // возвращаем исходные точки в случае ошибки
        }
        
        // Декодируем полилинию из ответа
        const route = response.data.routes[0];
        const polyline = L.Polyline.fromEncoded(route.geometry);
        return polyline.getLatLngs();
      } catch (error) {
        console.error('Error getting route by road:', error);
        return points; // возвращаем исходные точки в случае ошибки
      }
    },
    async searchLocation() {
      if (!this.searchAddress) return;
      
      try {
        // Используем Nominatim для геокодирования
        const response = await axios.get(`https://nominatim.openstreetmap.org/search`, {
          params: {
            q: this.searchAddress,
            format: 'json',
            limit: 1
          }
        });
        
        if (response.data && response.data.length > 0) {
          const result = response.data[0];
          const lat = parseFloat(result.lat);
          const lng = parseFloat(result.lon);
          
          // Перемещаем карту к найденному месту
          this.map.setView([lat, lng], 15);
          
          // Добавляем или обновляем маркер поиска
          if (this.searchMarker) {
            this.searchMarker.setLatLng([lat, lng]);
          } else {
            this.searchMarker = L.marker([lat, lng], {
              icon: L.divIcon({
                className: 'search-marker',
                html: `<div style="background-color: #ff9800; width: 15px; height: 15px; border-radius: 50%; border: 3px solid white;"></div>`,
                iconSize: [21, 21]
              })
            }).addTo(this.map);
          }
          
          // Показываем информацию о найденном месте
          this.searchMarker.bindPopup(`
            <strong>${result.display_name}</strong>
          `).openPopup();
        } else {
          alert('Место не найдено. Попробуйте другой запрос.');
        }
      } catch (error) {
        console.error('Error searching location:', error);
        alert('Ошибка при поиске. Попробуйте позже.');
      }
    }
  }
}
</script>

<style scoped>
.map-view {
  display: flex;
  height: calc(100vh - 40px);
}

.map-container {
  flex: 3;
  display: flex;
  flex-direction: column;
}

.map-container h2 {
  margin-bottom: 10px;
}

.search-container {
  display: flex;
  margin-bottom: 10px;
  z-index: 10;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px 0 0 4px;
  font-size: 0.9rem;
}

.search-button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
}

.leaflet-map {
  flex: 1;
  min-height: 500px;
  border-radius: 6px;
  overflow: hidden;
  z-index: 1;
}

.map-controls {
  flex: 1;
  max-width: 300px;
  padding-left: 20px;
}

.depot-icon {
  background-color: #4a6cf7;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  border: 2px solid white;
}

.order-icon {
  background-color: #f74a4a;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  border: 2px solid white;
}

.map-layers .form-group {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
}

.map-layers .form-group input {
  margin-right: 8px;
}

/* Стили для маркеров начала/конца маршрута */
.start-marker {
  background-color: #4a6cf7;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}

.end-marker {
  background-color: #f74a4a;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}

/* Увеличиваем приоритет отображения маркеров */
.leaflet-marker-icon {
  z-index: 1000 !important;
}
</style> 