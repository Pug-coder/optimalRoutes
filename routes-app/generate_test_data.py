#!/usr/bin/env python3
"""
Скрипт для генерации тестовых данных в базу данных.
Создает депо, курьеров и заказы для тестирования алгоритмов маршрутизации.
"""

import asyncio
import uuid
import random
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.database import SessionLocal
from api.models import Location, Depot, Courier, Order
from api.models.order import OrderStatus


class TestDataGenerator:
    """Генератор тестовых данных для системы маршрутизации."""
    
    def __init__(self):
        # Московские районы с реальными координатами
        self.moscow_areas = [
            # Центральные районы
            {"name": "Центр", "lat": 55.7558, "lon": 37.6176},
            {"name": "Арбат", "lat": 55.7500, "lon": 37.5900},
            {"name": "Китай-город", "lat": 55.7539, "lon": 37.6300},
            {"name": "Замоскворечье", "lat": 55.7423, "lon": 37.6300},
            
            # Северные районы
            {"name": "Сокол", "lat": 55.7966, "lon": 37.5151},
            {"name": "Войковская", "lat": 55.8192, "lon": 37.4980},
            {"name": "Медведково", "lat": 55.8970, "lon": 37.6610},
            {"name": "Отрадное", "lat": 55.8640, "lon": 37.6040},
            
            # Восточные районы
            {"name": "Сокольники", "lat": 55.7892, "lon": 37.6792},
            {"name": "Преображенская", "lat": 55.7965, "lon": 37.7154},
            {"name": "Измайлово", "lat": 55.7881, "lon": 37.7854},
            {"name": "Новогиреево", "lat": 55.7511, "lon": 37.8174},
            
            # Южные районы
            {"name": "Коломенская", "lat": 55.6785, "lon": 37.6641},
            {"name": "Автозаводская", "lat": 55.7065, "lon": 37.6587},
            {"name": "Царицыно", "lat": 55.6196, "lon": 37.6687},
            {"name": "Орехово", "lat": 55.6127, "lon": 37.6927},
            
            # Западные районы
            {"name": "Университет", "lat": 55.6924, "lon": 37.5346},
            {"name": "Проспект Вернадского", "lat": 55.6760, "lon": 37.5076},
            {"name": "Юго-Западная", "lat": 55.6634, "lon": 37.4829},
            {"name": "Крылатское", "lat": 55.7567, "lon": 37.4080},
            
            # Северо-западные районы
            {"name": "Тушино", "lat": 55.8267, "lon": 37.4356},
            {"name": "Строгино", "lat": 55.8024, "lon": 37.4024},
            {"name": "Щукинская", "lat": 55.8092, "lon": 37.4634},
            
            # Юго-восточные районы
            {"name": "Люблино", "lat": 55.6755, "lon": 37.7625},
            {"name": "Печатники", "lat": 55.6916, "lon": 37.7313},
            {"name": "Текстильщики", "lat": 55.7084, "lon": 37.7313},
        ]
        
        # Имена для курьеров
        self.courier_names = [
            "Александр Петров", "Михаил Сидоров", "Дмитрий Иванов", 
            "Сергей Козлов", "Андрей Морозов", "Владимир Новиков", 
            "Николай Волков", "Алексей Соколов", "Артем Лебедев", 
            "Максим Попов", "Евгений Орлов", "Роман Медведев",
            "Игорь Федоров", "Денис Захаров", "Олег Смирнов", 
            "Павел Кузнецов"
        ]
        
        # Имена клиентов
        self.customer_names = [
            "Анна Иванова", "Елена Петрова", "Мария Сидорова", 
            "Татьяна Козлова", "Ольга Морозова", "Наталья Новикова", 
            "Екатерина Волкова", "Ирина Соколова", "Юлия Лебедева", 
            "Светлана Попова", "Людмила Орлова", "Галина Медведева",
            "Валентина Федорова", "Надежда Захарова", "Тамара Смирнова", 
            "Вера Кузнецова", "Борис Васильев", "Геннадий Тихонов", 
            "Виктор Степанов", "Константин Белов", "Леонид Красиков", 
            "Валерий Чернов", "Владислав Рыжов", "Станислав Зеленов"
        ]

    def _generate_random_coordinate_near(
        self, 
        base_lat: float, 
        base_lon: float, 
        radius_km: float = 5.0
    ) -> Tuple[float, float]:
        """Генерирует случайные координаты в радиусе от базовой точки."""
        # Примерные коэффициенты для Москвы 
        # (1 градус ≈ 111 км по широте, ≈ 64 км по долготе)
        lat_range = radius_km / 111.0
        lon_range = radius_km / 64.0
        
        lat = base_lat + random.uniform(-lat_range, lat_range)
        lon = base_lon + random.uniform(-lon_range, lon_range)
        
        return round(lat, 6), round(lon, 6)

    async def clear_existing_data(self, db: AsyncSession):
        """Очищает существующие тестовые данные."""
        print("Очистка существующих данных...")
        
        # Удаляем в правильном порядке из-за foreign key constraints
        await db.execute(text("DELETE FROM route_points"))
        await db.execute(text("DELETE FROM routes"))
        await db.execute(text("DELETE FROM orders"))
        await db.execute(text("DELETE FROM couriers"))
        await db.execute(text("DELETE FROM depots"))
        await db.execute(text("DELETE FROM locations"))
        
        await db.commit()
        print("Данные очищены")

    async def create_locations(
        self, 
        db: AsyncSession, 
        count: int
    ) -> List[Location]:
        """Создает локации для заказов."""
        print(f"Создание {count} локаций...")
        
        locations = []
        for i in range(count):
            # Выбираем случайный район Москвы
            area = random.choice(self.moscow_areas)
            
            # Генерируем координаты рядом с центром района
            lat, lon = self._generate_random_coordinate_near(
                area["lat"], area["lon"], radius_km=3.0
            )
            
            location = Location(
                id=f"test_location_{i:04d}",
                latitude=lat,
                longitude=lon,
                address=f"Тестовый адрес {i+1}, район {area['name']}, Москва"
            )
            
            db.add(location)
            locations.append(location)
        
        await db.commit()
        print(f"Создано {len(locations)} локаций")
        return locations

    async def create_depots(
        self, 
        db: AsyncSession, 
        depot_count: int = 3
    ) -> List[Depot]:
        """Создает депо."""
        print(f"Создание {depot_count} депо...")
        
        # Выбираем стратегически важные точки для депо
        depot_locations = [
            {"name": "Северный", "lat": 55.8267, "lon": 37.4356},  # Тушино
            {"name": "Восточный", "lat": 55.7881, "lon": 37.7854},  # Измайлово
            {"name": "Южный", "lat": 55.6196, "lon": 37.6687},     # Царицыно
            {"name": "Западный", "lat": 55.7567, "lon": 37.4080},  # Крылатское
            {"name": "Центральный", "lat": 55.7558, "lon": 37.6176}  # Центр
        ]
        
        depots = []
        for i in range(min(depot_count, len(depot_locations))):
            depot_info = depot_locations[i]
            
            # Создаем локацию для депо
            location = Location(
                id=f"depot_location_{i}",
                latitude=depot_info["lat"],
                longitude=depot_info["lon"],
                address=f"Депо {depot_info['name']}, Москва"
            )
            db.add(location)
            
            # Создаем депо
            depot = Depot(
                id=uuid.uuid4(),
                name=f"Депо {depot_info['name']}",
                location_id=location.id
            )
            db.add(depot)
            depots.append(depot)
        
        await db.commit()
        print(f"Создано {len(depots)} депо")
        return depots

    async def create_couriers(
        self, 
        db: AsyncSession, 
        depots: List[Depot], 
        couriers_per_depot: int = 3
    ) -> List[Courier]:
        """Создает курьеров."""
        total_couriers = len(depots) * couriers_per_depot
        print(f"Создание {total_couriers} курьеров "
              f"({couriers_per_depot} на депо)...")
        
        couriers = []
        name_index = 0
        
        for depot in depots:
            for i in range(couriers_per_depot):
                if name_index >= len(self.courier_names):
                    name_index = 0
                
                courier = Courier(
                    id=uuid.uuid4(),
                    name=self.courier_names[name_index],
                    phone=f"+7{random.randint(9000000000, 9999999999)}",
                    depot_id=depot.id,
                    max_capacity=random.randint(10, 20),
                    max_weight=random.uniform(60.0, 100.0),
                    max_distance=random.uniform(80.0, 120.0)
                )
                
                db.add(courier)
                couriers.append(courier)
                name_index += 1
        
        await db.commit()
        print(f"Создано {len(couriers)} курьеров")
        return couriers

    async def create_orders(
        self, 
        db: AsyncSession, 
        locations: List[Location], 
        depots: List[Depot],
        order_count: int
    ) -> List[Order]:
        """Создает заказы и назначает их на ближайшие депо."""
        print(f"Создание {order_count} заказов...")
        
        orders = []
        for i in range(order_count):
            # Выбираем случайную локацию
            location = random.choice(locations)
            
            # Находим ближайшее депо
            closest_depot = None
            min_distance = float('inf')
            
            for depot in depots:
                # Получаем координаты депо из его location_id
                if depot.location_id.startswith("depot_location_"):
                    depot_index = int(depot.location_id.split("_")[-1])
                    if depot_index < len(self.moscow_areas):
                        # Используем координаты из depot_locations 
                        # в create_depots
                        depot_locations = [
                            {"lat": 55.8267, "lon": 37.4356},  # Северный
                            {"lat": 55.7881, "lon": 37.7854},  # Восточный
                            {"lat": 55.6196, "lon": 37.6687},  # Южный
                            {"lat": 55.7567, "lon": 37.4080},  # Западный
                            {"lat": 55.7558, "lon": 37.6176}   # Центральный
                        ]
                        if depot_index < len(depot_locations):
                            depot_lat = depot_locations[depot_index]["lat"]
                            depot_lon = depot_locations[depot_index]["lon"]
                
                # Вычисляем приблизительное расстояние
                distance = ((location.latitude - depot_lat) ** 2 + 
                            (location.longitude - depot_lon) ** 2) ** 0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_depot = depot
            
            # Выбираем случайное имя клиента
            customer_name = random.choice(self.customer_names)
            
            order = Order(
                id=uuid.uuid4(),
                customer_name=customer_name,
                customer_phone=f"+7{random.randint(9000000000, 9999999999)}",
                location_id=location.id,
                items_count=random.randint(1, 4),  # Уменьшил с 1-5 до 1-4
                weight=random.uniform(0.5, 6.0),   # Уменьшил с 0.5-8.0 до 0.5-6.0 кг
                status=OrderStatus.PENDING,
                # Назначаем на ближайшее депо
                depot_id=closest_depot.id if closest_depot else None
            )
            
            db.add(order)
            orders.append(order)
        
        await db.commit()
        print(f"Создано {len(orders)} заказов")
        return orders

    async def generate_small_test_data(self, db: AsyncSession):
        """Генерирует данные для малого теста (30 заказов)."""
        print("\n=== ГЕНЕРАЦИЯ ДАННЫХ ДЛЯ МАЛОГО ТЕСТА ===")
        
        # Создаем 2 депо
        depots = await self.create_depots(db, depot_count=2)
        
        # Создаем 6 курьеров (3 на депо)
        couriers = await self.create_couriers(db, depots, couriers_per_depot=3)
        
        # Создаем 35 локаций и 30 заказов
        locations = await self.create_locations(db, count=35)
        orders = await self.create_orders(db, locations, depots, order_count=30)
        
        print("\n✅ МАЛЫЙ ТЕСТ ГОТОВ:")
        print(f"   📍 Депо: {len(depots)}")
        print(f"   🚗 Курьеры: {len(couriers)}")
        print(f"   📦 Заказы: {len(orders)}")
        print(f"   📍 Локации: {len(locations)}")

    async def generate_medium_test_data(self, db: AsyncSession):
        """Генерирует данные для среднего теста (60 заказов)."""
        print("\n=== ГЕНЕРАЦИЯ ДАННЫХ ДЛЯ СРЕДНЕГО ТЕСТА ===")
        
        # Создаем 3 депо
        depots = await self.create_depots(db, depot_count=3)
        
        # Создаем 12 курьеров (4 на депо)
        couriers = await self.create_couriers(db, depots, couriers_per_depot=4)
        
        # Создаем 70 локаций и 60 заказов
        locations = await self.create_locations(db, count=70)
        orders = await self.create_orders(db, locations, depots, order_count=60)
        
        print("\n✅ СРЕДНИЙ ТЕСТ ГОТОВ:")
        print(f"   📍 Депо: {len(depots)}")
        print(f"   🚗 Курьеры: {len(couriers)}")
        print(f"   📦 Заказы: {len(orders)}")
        print(f"   📍 Локации: {len(locations)}")

    async def generate_large_test_data(self, db: AsyncSession):
        """Генерирует данные для большого теста (100 заказов)."""
        print("\n=== ГЕНЕРАЦИЯ ДАННЫХ ДЛЯ БОЛЬШОГО ТЕСТА ===")
        
        # Создаем 4 депо
        depots = await self.create_depots(db, depot_count=4)
        
        # Создаем 16 курьеров (4 на депо)
        couriers = await self.create_couriers(db, depots, couriers_per_depot=4)
        
        # Создаем 120 локаций и 100 заказов
        locations = await self.create_locations(db, count=120)
        orders = await self.create_orders(db, locations, depots, order_count=100)
        
        print("\n✅ БОЛЬШОЙ ТЕСТ ГОТОВ:")
        print(f"   📍 Депо: {len(depots)}")
        print(f"   🚗 Курьеры: {len(couriers)}")
        print(f"   📦 Заказы: {len(orders)}")
        print(f"   📍 Локации: {len(locations)}")

    async def generate_stress_test_data(self, db: AsyncSession):
        """Генерирует данные для стресс-теста (500+ заказов)."""
        print("\n=== ГЕНЕРАЦИЯ ДАННЫХ ДЛЯ СТРЕСС-ТЕСТА ===")
        
        # Создаем 5 депо
        depots = await self.create_depots(db, depot_count=5)
        
        # Создаем 25 курьеров (5 на депо)
        couriers = await self.create_couriers(db, depots, couriers_per_depot=5)
        
        # Создаем 500 локаций и 500 заказов
        locations = await self.create_locations(db, count=500)
        orders = await self.create_orders(db, locations, depots, order_count=500)
        
        print("\n✅ СТРЕСС-ТЕСТ ГОТОВ:")
        print(f"   📍 Депо: {len(depots)}")
        print(f"   🚗 Курьеры: {len(couriers)}")
        print(f"   📦 Заказы: {len(orders)}")
        print(f"   📍 Локации: {len(locations)}")

    async def generate_algorithm_comparison_tests(self, db: AsyncSession):
        """Генерирует все тесты для сравнения алгоритмов (30, 60, 100 заказов)."""
        print("\n=== ГЕНЕРАЦИЯ ТЕСТОВ ДЛЯ СРАВНЕНИЯ АЛГОРИТМОВ ===")
        
        print("\n🔄 Тест 1/3: 30 заказов")
        await self.generate_small_test_data(db)
        
        input("\nНажмите Enter для продолжения к тесту с 60 заказами...")
        await self.clear_existing_data(db)
        
        print("\n🔄 Тест 2/3: 60 заказов")
        await self.generate_medium_test_data(db)
        
        input("\nНажмите Enter для продолжения к тесту с 100 заказами...")
        await self.clear_existing_data(db)
        
        print("\n🔄 Тест 3/3: 100 заказов")
        await self.generate_large_test_data(db)
        
        print("\n🎯 ВСЕ ТЕСТЫ ДЛЯ СРАВНЕНИЯ АЛГОРИТМОВ ГОТОВЫ!")
        print("   Теперь можно проводить сравнительное тестирование")


async def main():
    """Основная функция."""
    print("🚀 Запуск генератора тестовых данных...")
    
    generator = TestDataGenerator()
    
    # Получаем сессию БД
    async with SessionLocal() as db:
        try:
            # Очищаем существующие данные
            await generator.clear_existing_data(db)
            
            # Спрашиваем пользователя, какой тест генерировать
            print("\nВыберите тип теста:")
            print("1. Малый тест (2 депо, 6 курьеров, 30 заказов)")
            print("2. Средний тест (3 депо, 12 курьеров, 60 заказов)")
            print("3. Большой тест (4 депо, 16 курьеров, 100 заказов)")
            print("4. Стресс-тест (5 депо, 25 курьеров, 500 заказов)")
            print("5. Тесты для сравнения алгоритмов (30, 60, 100 заказов)")
            print("6. Все тесты")
            
            choice = input("Введите номер (1-6): ").strip()
            
            if choice == "1":
                await generator.generate_small_test_data(db)
            elif choice == "2":
                await generator.generate_medium_test_data(db)
            elif choice == "3":
                await generator.generate_large_test_data(db)
            elif choice == "4":
                await generator.generate_stress_test_data(db)
            elif choice == "5":
                await generator.generate_algorithm_comparison_tests(db)
            elif choice == "6":
                await generator.generate_small_test_data(db)
                await generator.clear_existing_data(db)
                await generator.generate_medium_test_data(db)
                await generator.clear_existing_data(db)
                await generator.generate_large_test_data(db)
                await generator.clear_existing_data(db)
                await generator.generate_stress_test_data(db)
            else:
                print("Неверный выбор. Генерируем малый тест по умолчанию.")
                await generator.generate_small_test_data(db)
            
            print("\n🎉 Генерация данных завершена успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка при генерации данных: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main()) 