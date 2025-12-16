# Proyecto Final: Sistema de Trading Algorítmico en Polymarket

## Descripción

Este proyecto corresponde a la práctica final del Máster, diseñada para presentar un sistema de trading algorítmico. Nuestro objetivo es demostrar la capacidad de combinar **blockchain**, **algoritmos de trading** y una **visión estratégica en mercados financieros emergentes**, en particular en plataformas de predicción como **Polymarket**.

Para el desarrollo de la práctica, nos hemos centrado exclusivamente en los **mercados de Polymarket con vencimiento a 15 minutos, en los que los participantes operan sobre si el precio de Bitcoin subirá o bajará antes del cierre del mercado**. Este tipo de mercado se ha seleccionado por su horizonte temporal corto, que favorece una dinámica de precios activa y una liquidez suficiente para evaluar el comportamiento del sistema mediante múltiples operaciones en intervalos reducidos de tiempo.

El sistema implementado permite:  

- **Conexión en tiempo real con Polymarket**: nuestro algoritmo interactúa directamente con el mercado seleccionado para obtener precios, volúmenes y datos relevantes.  
- **Estimación de precio justo (mid-price) mediante filtro de Kalman**: aplicamos un filtro de Kalman para suavizar las fluctuaciones del mercado y obtener una estimación más precisa del valor de referencia de cada activo.  
- **Gestión de spread y cotización**: el sistema determina márgenes adecuados y ejecuta órdenes ya sea en streaming o bajo condiciones definidas, asegurando eficiencia y consistencia.  
- **Simulación y operativa controlada**: el sistema permite operar **tanto en modo simulación como en modo real**, utilizando una wallet especificada por el usuario. Este enfoque garantiza seguridad durante las pruebas y permite analizar el comportamiento del algoritmo mediante registros y visualizaciones de las órdenes enviadas al mercado.  

## Instalación

Clona el repositorio e instala las dependencias:

```bash
git clone https://github.com/SantiLC03/market-making-polymarket.git
cd market-making-polymarket
pip install -r requirements.txt```

## Uso
python main.py



Asegúrate de configurar tu wallet de prueba y las claves de API necesarias antes de iniciar la operativa.



