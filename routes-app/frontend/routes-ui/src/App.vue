<template>
  <div id="app">
    <div class="main-layout">
      <nav class="sidebar">
        <div class="app-title">
          <h1>Оптимизатор Маршрутов</h1>
        </div>
        <div class="nav-links">
          <router-link to="/" exact>Карта</router-link>
          <router-link to="/depots">Склады</router-link>
          <router-link to="/couriers">Курьеры</router-link>
          <router-link to="/orders">Заказы</router-link>
          <router-link to="/optimize">Оптимизация</router-link>
        </div>
      </nav>
      <main class="content">
        <router-view/>
      </main>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Roboto', Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-layout {
  display: flex;
  height: 100%;
}

.sidebar {
  width: 250px;
  background-color: #2c3e50;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.app-title {
  padding: 0 20px 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.app-title h1 {
  font-size: 1.2rem;
  font-weight: 500;
}

.nav-links {
  display: flex;
  flex-direction: column;
  margin-top: 20px;
}

.nav-links a {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  padding: 12px 20px;
  transition: all 0.3s ease;
}

.nav-links a:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-links a.router-link-active {
  background-color: rgba(255, 255, 255, 0.15);
  color: white;
  border-left: 3px solid #42b983;
}

.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

/* Базовые стили компонентов */
button, .btn {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.3s;
}

button:hover, .btn:hover {
  background-color: #3aa876;
}

input, select, textarea {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.card {
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th, .table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.table th {
  font-weight: 500;
  background-color: #f9f9f9;
}
</style>
