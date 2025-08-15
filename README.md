# Invest Portfolio Backend

Este proyecto es una API backend desarrollada en Django y Django REST Framework para la gestión de portafolios de inversión.

## Características principales
- **Gestión de portafolios:** Permite a los usuarios crear, consultar y administrar múltiples portafolios de inversión personales.
- **Activos y transacciones:** Los usuarios pueden agregar activos (acciones) a sus portafolios y registrar transacciones de compra.
- **Cálculo de rendimiento:** Calcula automáticamente el rendimiento de cada activo y del portafolio completo, mostrando métricas como coste total, valor actual, ganancia/pérdida y porcentaje de rendimiento.
- **API segura:** Solo el usuario autenticado puede acceder y modificar su información y portafolios.
- **Integración con Yahoo Finance:** Obtiene cotizaciones y datos de mercado en tiempo real usando la librería `yfinance`.

## Tecnologías utilizadas
- Python 3
- Django
- Django REST Framework
- PostgreSQL
- yfinance

## Instalación y uso
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Configura las variables de entorno y la base de datos en el archivo `.env`.
3. Realiza las migraciones:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
4. Ejecuta el servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```

## Estructura principal
- `accounts/`: Gestión de usuarios y autenticación.
- `portfolio/`: Lógica de portafolios, activos y transacciones.
- `investportfolio/`: Configuración principal del proyecto.

## API
La API sigue principios REST y requiere autenticación. Los endpoints principales permiten:
- Crear y consultar portafolios
- Agregar activos y registrar transacciones
- Consultar métricas agregadas y cotizaciones de mercado
