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

  console.log('Decoding polyline:', encoded.substring(0, 50) + '...');

  try {
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

      const decodedLat = lat * 1e-5;
      const decodedLng = lng * 1e-5;

      // Детальная проверка координат
      if (isNaN(decodedLat) || isNaN(decodedLng)) {
        console.error('NaN coordinates detected in polyline decode:', { lat, lng, decodedLat, decodedLng, index });
        continue;
      }

      // Проверяем, что координаты валидны
      if (decodedLat >= -90 && decodedLat <= 90 &&
          decodedLng >= -180 && decodedLng <= 180) {
        points.push(L.latLng([decodedLat, decodedLng]));
      } else {
        console.warn('Invalid coordinate range:', { decodedLat, decodedLng });
      }
    }
  } catch (e) {
    console.error('Error decoding polyline:', e);
  }

  console.log('Decoded points count:', points.length);
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

// Расширяем прототип Polyline для безопасной анимации
const originalSnakeIn = L.Polyline.prototype.snakeIn;
L.Polyline.prototype.snakeIn = function() {
  try {
    // Проверяем, что у линии есть валидные точки
    const points = this.getLatLngs();
    if (!points || points.length < 2 || points.some(p => isNaN(p.lat) || isNaN(p.lng))) {
      console.warn('Cannot animate polyline with invalid points');
      this.setStyle({ opacity: 0.8 }); // Просто показываем линию без анимации
      return this;
    }
    
    // Вызываем оригинальный метод
    return originalSnakeIn.call(this);
  } catch (e) {
    console.error('Error in snakeIn:', e);
    this.setStyle({ opacity: 0.8 }); // Просто показываем линию без анимации
    return this;
  }
};

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

        // Используем новый endpoint с координатами
        const routesResponse = await axios.get(`${API_BASE_URL}/routes/with-locations`)
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
          const marker = L.marker([depot.location.latitude, depot.location.longitude], {
            icon: L.divIcon({
              className: 'depot-marker',
              html: `<div class="depot-icon">D</div>`,
              iconSize: [24, 24]
            })
          })
          
          const popup = L.popup({
            className: 'depot-popup'
          }).setContent(`
            <strong>Склад: ${depot.name}</strong><br>
            Адрес: ${depot.location.address || 'Нет адреса'}
          `)
          
          marker.bindPopup(popup)
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
          
          const marker = L.marker([order.location.latitude, order.location.longitude], {
            icon: L.divIcon({
              className: 'order-marker',
              html: `<div class="order-icon" style="background-color: ${markerColor}; border-radius: 50%;">O</div>`,
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
          
          const popup = L.popup({
            className: 'order-popup'
          }).setContent(`
            <strong>Заказ #${order.id}</strong><br>
            Клиент: ${order.customer_name || 'Нет имени'}<br>
            Адрес: ${order.location.address || 'Нет адреса'}<br>
            Вес: ${order.weight} кг${courierInfo}
            <br>Статус: ${order.status === 'assigned' ? 'Назначен' : 'Ожидает назначения'}
          `)
          
          marker.bindPopup(popup)
          this.orderMarkers.addLayer(marker)
        }
      })
    },
    async renderRoutes() {
      this.routeLines.clearLayers()
      
      console.log('Starting renderRoutes, routes count:', this.routes.length);
      
      // Generate different colors for each route
      const getRouteColor = (index) => {
        const colors = ['#FF5733', '#33FF57', '#3357FF', '#F033FF', '#FF33A8', '#33FFF5', '#FFD433']
        return colors[index % colors.length]
      }
      
      if (this.routes && this.routes.length) {
        for (const [index, route] of this.routes.entries()) {
          console.log(`Processing route ${index}:`, route);
          
          if (route.points && route.points.length > 0 && route.depot_location) {
            // Точки маршрута - склад в начале, затем заказы, затем возврат на склад
            const routePoints = [];
            
            console.log('Depot location:', route.depot_location);
            
            // Проверяем валидность координат депо
            if (route.depot_location.latitude != null && 
                route.depot_location.longitude != null &&
                !isNaN(route.depot_location.latitude) && 
                !isNaN(route.depot_location.longitude) &&
                isFinite(route.depot_location.latitude) &&
                isFinite(route.depot_location.longitude)) {
              
              // Добавляем склад в начало маршрута
              const depotCoords = [route.depot_location.latitude, route.depot_location.longitude];
              console.log('Adding depot coordinates:', depotCoords);
              routePoints.push(depotCoords);
              
              // Добавляем заказы
              for (const [pointIndex, point] of route.points.entries()) {
                console.log(`Processing point ${pointIndex}:`, point);
                
                if (point.order_location && 
                    point.order_location.latitude != null && 
                    point.order_location.longitude != null &&
                    !isNaN(point.order_location.latitude) && 
                    !isNaN(point.order_location.longitude) &&
                    isFinite(point.order_location.latitude) &&
                    isFinite(point.order_location.longitude)) {
                  
                  const orderCoords = [point.order_location.latitude, point.order_location.longitude];
                  console.log(`Adding order coordinates for point ${pointIndex}:`, orderCoords);
                  routePoints.push(orderCoords);
                } else {
                  console.error(`Invalid order location for point ${pointIndex}:`, point.order_location);
                }
              }
              
              // Добавляем склад в конец маршрута
              console.log('Adding return depot coordinates:', depotCoords);
              routePoints.push(depotCoords);
            } else {
              console.error('Invalid depot location:', route.depot_location);
            }
            
            console.log(`Route ${index} final points:`, routePoints);
            
            if (routePoints.length > 1) {
              // Получаем маршрут по дорогам
              try {
                // Разбиваем на сегменты, чтобы избежать ограничений API
                const segments = [];
                for (let i = 0; i < routePoints.length - 1; i++) {
                  const segment = [routePoints[i], routePoints[i + 1]];
                  console.log(`Segment ${i}:`, segment);
                  segments.push(segment);
                }
                
                // Добавляем маркеры начала и конца маршрута
                const startCoords = routePoints[0];
                const endCoords = routePoints[routePoints.length - 1];
                
                console.log('Start marker coordinates:', startCoords);
                console.log('End marker coordinates:', endCoords);
                
                const startMarker = L.marker(startCoords, {
                  icon: L.divIcon({
                    className: 'start-marker',
                    html: `<div style="width: 20px; height: 20px; background-color: #4a6cf7; border: 3px solid white; border-radius: 50%;"></div>`,
                    iconSize: [26, 26]
                  }),
                  title: 'Старт',
                  zIndexOffset: 1000
                });
                
                const endMarker = L.marker(endCoords, {
                  icon: L.divIcon({
                    className: 'end-marker',
                    html: `<div style="width: 20px; height: 20px; background-color: #f74a4a; border: 3px solid white; border-radius: 50%;"></div>`,
                    iconSize: [26, 26]
                  }),
                  title: 'Финиш',
                  zIndexOffset: 1000
                });
                
                startMarker.bindPopup(L.popup({
                  className: 'route-start-popup'
                }).setContent(`<strong>Начало маршрута</strong><br>Склад: ${route.depot_location.address || 'Без адреса'}`));
                
                endMarker.bindPopup(L.popup({
                  className: 'route-end-popup'
                }).setContent(`<strong>Конец маршрута</strong><br>Склад: ${route.depot_location.address || 'Без адреса'}`));
                
                this.routeLines.addLayer(startMarker);
                this.routeLines.addLayer(endMarker);
                
                // Создаем маршрут по дорогам для каждого сегмента
                let errorSegments = 0;
                for (let i = 0; i < segments.length; i++) {
                  const segment = segments[i];
                  console.log(`Processing segment ${i} for route ${index}:`, segment);
                  
                  try {
                    // Проверяем валидность сегмента
                    if (!segment || segment.length !== 2 || 
                        !Array.isArray(segment[0]) || !Array.isArray(segment[1])) {
                      throw new Error('Invalid segment format');
                    }

                    const roadPoints = await this.getRouteByRoad(segment);
                    console.log(`Got road points for segment ${i}:`, roadPoints.length, 'points');
                    
                    // Особая обработка для сегмента возврата в депо
                    const isReturnSegment = i === segments.length - 1;
                    
                    const routeLine = L.polyline(roadPoints, {
                      color: getRouteColor(index),
                      weight: isReturnSegment ? 5 : 4, // Делаем линию возврата немного толще
                      opacity: 0.7,
                      // Для сегмента возврата в депо добавляем пунктир
                      dashArray: isReturnSegment ? '10, 10' : null
                    });
                    
                    routeLine.bindPopup(`
                      <strong>Маршрут #${route.id}</strong><br>
                      ${isReturnSegment ? '<strong>Возврат в депо</strong><br>' : ''}
                      Курьер: ${route.courier_id}<br>
                      Кол-во заказов: ${route.points.length}<br>
                      Дистанция: ${route.total_distance.toFixed(2)} км
                    `);
                    
                    this.routeLines.addLayer(routeLine);
                    
                    // Добавляем анимацию
                    setTimeout(() => {
                      if (routeLine) {
                        console.log(`Starting animation for route ${index}, segment ${i}`);
                        routeLine.snakeIn();
                      }
                    }, 100 * index + 50 * i);
                  } catch (error) {
                    console.error(`Error rendering segment ${i} by road:`, error);
                    errorSegments += 1;
                    
                    // Отображаем этот сегмент как прямую линию при ошибке
                    const fallbackLine = L.polyline(segment, {
                      color: getRouteColor(index),
                      weight: 3,
                      opacity: 0.7,
                      dashArray: '5, 10'
                    });
                    
                    // Добавляем информацию, является ли это сегментом возврата в депо
                    const isReturnSegment = i === segments.length - 1;
                    
                    // Если это сегмент возврата, используем более заметный стиль
                    if (isReturnSegment) {
                      fallbackLine.setStyle({
                        weight: 4,
                        dashArray: '10, 5'
                      });
                    }
                    
                    fallbackLine.bindPopup(`
                      <strong>Маршрут #${route.id} (резервный)</strong><br>
                      ${isReturnSegment ? '<strong>Возврат в депо</strong><br>' : ''}
                      Курьер: ${route.courier_id}<br>
                      Сегмент ${i+1}/${segments.length}
                    `);
                    
                    this.routeLines.addLayer(fallbackLine);
                    
                    // Добавляем анимацию для резервной линии
                    setTimeout(() => {
                      if (fallbackLine) {
                        console.log(`Starting fallback animation for route ${index}, segment ${i}`);
                        fallbackLine.snakeIn();
                      }
                    }, 100 * index + 50 * i);
                  }
                }
                
                if (errorSegments > 0) {
                  console.warn(`Route #${route.id}: ${errorSegments} segments had rendering errors and were displayed as fallback lines`);
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
                
                // Добавляем анимацию для прямых линий
                setTimeout(() => {
                  if (routeLine) {
                    console.log(`Starting direct line animation for route ${index}`);
                    routeLine.snakeIn();
                  }
                }, 100 * index);
                
                // Выделяем сегмент возврата в депо
                if (routePoints.length >= 2) {
                  const returnSegment = [
                    routePoints[routePoints.length - 2], 
                    routePoints[routePoints.length - 1]
                  ];
                  
                  const returnLine = L.polyline(returnSegment, {
                    color: getRouteColor(index),
                    weight: 4,
                    opacity: 0.8,
                    dashArray: '10, 5'
                  });
                  
                  returnLine.bindPopup(`
                    <strong>Маршрут #${route.id} - Возврат в депо</strong><br>
                    Курьер: ${route.courier_id}<br>
                    Резервная линия
                  `);
                  
                  this.routeLines.addLayer(returnLine);
                  
                  // Анимируем линию возврата в депо
                  setTimeout(() => {
                    if (returnLine) {
                      console.log(`Starting return line animation for route ${index}`);
                      returnLine.snakeIn();
                    }
                  }, 100 * index + 50);
                }
              }
            } else {
              console.warn(`Route ${index} has insufficient points:`, routePoints.length);
            }
          } else {
            console.warn(`Route ${index} missing points or depot location:`, { 
              hasPoints: !!route.points, 
              pointsLength: route.points?.length, 
              hasDepotLocation: !!route.depot_location 
            });
          }
        }
      }
      
      console.log('Finished renderRoutes');
    },
    // Получение маршрута по реальным дорогам
    async getRouteByRoad(points) {
      console.log('getRouteByRoad input points:', points);
      
      if (!points || points.length < 2) {
        console.warn('getRouteByRoad: insufficient points');
        return points;
      }
      
      // Проверяем валидность входных координат
      const validPoints = points.filter((point, index) => {
        const isValid = Array.isArray(point) && 
          point.length === 2 && 
          typeof point[0] === 'number' && typeof point[1] === 'number' &&
          !isNaN(point[0]) && !isNaN(point[1]) &&
          isFinite(point[0]) && isFinite(point[1]) &&
          point[0] >= -90 && point[0] <= 90 && 
          point[1] >= -180 && point[1] <= 180;
        
        if (!isValid) {
          console.error(`Invalid point at index ${index}:`, point);
        }
        
        return isValid;
      });
      
      console.log(`Valid points: ${validPoints.length}/${points.length}`);
      
      if (validPoints.length < 2) {
        console.warn('Not enough valid points for routing');
        return points;
      }
      
      try {
        // Формируем строку координат для OSRM API
        const coordinates = validPoints.map(point => `${point[1]},${point[0]}`).join(';');
        console.log('OSRM request coordinates:', coordinates);
        
        const response = await axios.get(`${OSRM_API_URL}${coordinates}?overview=full&geometries=polyline`);
        
        console.log('OSRM response:', response.data);
        
        if (response.data.code !== 'Ok' || !response.data.routes || !response.data.routes.length) {
          console.error('OSRM error:', response.data);
          return validPoints; // возвращаем валидные исходные точки в случае ошибки
        }
        
        // Декодируем полилинию из ответа
        const route = response.data.routes[0];
        console.log('Route geometry:', route.geometry);
        
        const polyline = L.Polyline.fromEncoded(route.geometry);
        const latLngs = polyline.getLatLngs();
        
        console.log('Decoded latLngs count:', latLngs.length);
        
        // Проверяем полученные координаты на валидность
        const validLatLngs = latLngs.filter((coord, index) => {
          // Проверяем, что координаты не NaN и находятся в допустимых диапазонах
          const isValid = coord && 
                 typeof coord.lat === 'number' && typeof coord.lng === 'number' &&
                 !isNaN(coord.lat) && !isNaN(coord.lng) &&
                 isFinite(coord.lat) && isFinite(coord.lng) &&
                 coord.lat >= -90 && coord.lat <= 90 && 
                 coord.lng >= -180 && coord.lng <= 180;
          
          if (!isValid) {
            console.error(`Invalid decoded coordinate at index ${index}:`, coord);
          }
          
          return isValid;
        });
        
        console.log(`Valid decoded coordinates: ${validLatLngs.length}/${latLngs.length}`);
        
        // Если после фильтрации осталось слишком мало точек, возвращаем исходные
        if (validLatLngs.length < 2) {
          console.warn('OSRM returned too few valid coordinates, using direct line');
          return validPoints;
        }
        
        return validLatLngs;
      } catch (error) {
        console.error('Error getting route by road:', error);
        return validPoints; // возвращаем валидные исходные точки в случае ошибки
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
          this.searchMarker.bindPopup(L.popup({
            className: 'search-popup'
          }).setContent(`
            <strong>${result.display_name}</strong>
          `)).openPopup();
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
  border-radius: 50% !important;
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

/* Стили для круглых попапов */
:deep(.leaflet-popup-content-wrapper) {
  border-radius: 15px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

:deep(.leaflet-popup-tip) {
  border-radius: 50% !important;
}

/* Специальные стили для попапов заказов */
:deep(.leaflet-popup-content) {
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.4;
}

/* Стили для попапов маркеров заказов */
.order-marker + .leaflet-popup :deep(.leaflet-popup-content-wrapper) {
  background: linear-gradient(135deg, #f74a4a 0%, #ff6b6b 100%) !important;
  color: white !important;
  border-radius: 20px !important;
}

.order-marker + .leaflet-popup :deep(.leaflet-popup-tip) {
  background: #f74a4a !important;
  border: none !important;
  border-radius: 50% !important;
}

/* Стили для попапов маркеров складов */
.depot-marker + .leaflet-popup :deep(.leaflet-popup-content-wrapper) {
  background: linear-gradient(135deg, #4a6cf7 0%, #6c7bff 100%) !important;
  color: white !important;
  border-radius: 20px !important;
}

.depot-marker + .leaflet-popup :deep(.leaflet-popup-tip) {
  background: #4a6cf7 !important;
  border: none !important;
}
</style> 