# Proyecto Final: Sistema de Trading Algorítmico en Polymarket

## Descripción

Este proyecto corresponde a la práctica final de máster, diseñada para presentar un sistema de trading algorítmico. Nuestro objetivo es demostrar la capacidad de combinar **blockchain**, **algoritmos de trading** y una **visión estratégica en mercados financieros emergentes**, en particular en la plataformas de predicción **Polymarket**.

Para este proyecto, nos hemos centrado exclusivamente en el **mercado del ganador de la UEFA Champions League 2025**, dado que ofrece una mayor estabilidad, al concentrarse en un reducido grupo de 4 a 5 equipos con probabilidades significativas de triunfo y cerrando el mercado en junio, lo que facilita la implementación de estrategias de predicción más precisas y una operativa controlada.

El sistema implementado permite:  

- **Conexión en tiempo real con Polymarket**: nuestro algoritmo interactúa directamente con el mercado seleccionado para obtener precios, volúmenes y datos relevantes.  
- **Estimación de precio justo (mid-price) mediante filtro de Kalman**: aplicamos un filtro de Kalman para suavizar las fluctuaciones del mercado y obtener una estimación más precisa del valor de referencia de cada activo.  
- **Gestión de spread y cotización**: el sistema determina márgenes adecuados y ejecuta órdenes ya sea en streaming o bajo condiciones definidas, asegurando eficiencia y consistencia.  
- **Simulación y operativa controlada**: todas las operaciones se realizan con una wallet específica de prueba, garantizando seguridad y trazabilidad, con evidencia gráfica de órdenes enviadas al mercado.  

El enfoque de este proyecto es **demostrar el potencial tecnológico y estratégico del equipo**, más que profundizar en cálculos matemáticos complejos.

## Instalación

Clona el repositorio e instala las dependencias:

```bash
git clone https://github.com/SantiLC03/market-making-polymarket.git
cd market-making-polymarket
pip install -r requirements.txt```

## Uso
python main.py


Asegúrate de configurar tu wallet de prueba y las claves de API necesarias antes de iniciar la operativa.



