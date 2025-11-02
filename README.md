# PROYECTO FINAL: SISTEMA DE TRADING ALGORÍTMICO EN POLYMARKET 🤖

## DESCRIPCIÓN

Este proyecto corresponde a la práctica final de máster, diseñada para presentar un sistema de **trading algorítmico** en mercados de predicción. Nuestro objetivo es demostrar la capacidad de combinar **blockchain**, **algoritmos de trading** y una **visión estratégica** en mercados financieros emergentes, en particular en la plataforma de predicción **Polymarket**.

El sistema implementado está orientado al **mercado del ganador de la UEFA Champions League 2025**, que por su estructura (4-5 equipos principales) ofrece una operativa controlada y más estable, facilitando la implementación de estrategias de predicción y Market Making.

El proyecto integra:

* **Conexión en tiempo real con Polymarket** mediante REST API y WebSockets, obteniendo precios, volúmenes y libro de órdenes completo.
* **Estimación de FairPrice y MidPrice mediante filtro de Kalman**, suavizando la volatilidad de los precios y detectando tendencias de compra/venta. 
* **Cálculo de Spread Óptimo avanzado**, considerando volatilidad del mercado, inventario actual, aversión al riesgo y profundidad del libro de órdenes.
* **Gestión de Wallet y envío de órdenes** a Polymarket, ya sea en entorno de prueba o real, con firma de transacciones a través de MetaMask.
* **Arquitectura modular orientada a objetos (POO)**, facilitando escalabilidad, mantenimiento y legibilidad del código.

El enfoque principal es **demostrar el potencial tecnológico y estratégico del sistema**, más que profundizar en la teoría de probabilidad o en complejidad matemática.

---

## ÍNDICE
* [Tecnologías](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#tecnologias)
* [Instalación](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#instalacion)
* [Uso](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#uso)
* [Estructura del proyecto](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#estructura-del-proyecto)
* [Explicación de los módulos](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#explicacion-de-los-modulos)
* [Contribución](https://github.com/SantiLC03/market-making-polymarket/blob/Actualizar-README/README.md#contribucion)

---

## TECNOLOGÍAS 💻

El proyecto se basa en las siguientes herramientas y librerías:

* **Python 3.11+**
* **Librerías clave:**
    * `requests`, `websockets`, `asyncio`
    * `json`, `re`, `datetime`
    * `numpy`, `pandas`, **`pykalman`**
    * `matplotlib`
* **Polymarket API** (REST y WebSocket)
* **MetaMask** para gestión de wallet y firma de transacciones
* **Programación Orientada a Objetos (POO)**

---

## INSTALACIÓN ⚙️

Clona el repositorio e instala las dependencias usando `pip`:

```bash
git clone [https://github.com/SantiLC03/market-making-polymarket.git](https://github.com/SantiLC03/market-making-polymarket.git)
cd market-making-polymarket
pip install -r requirements.txt
```

## USO ▶️

Para ejecutar el proyecto, simplemente corre el script principal:

```bash
python main.py
```
⚠️ Nota: Asegúrate de tener MetaMask configurado si deseas enviar órdenes reales. En entorno de prueba, se puede operar con datos simulados.

## ESTRUCTURA DEL PROYECTO 📁
La arquitectura es modular y orientada a objetos para una clara separación de responsabilidades:

```plaintext
market-making-polymarket/
│
├─ api_polymarket.py    # Conexión a REST API y WebSocket de Polymarket
├─ kalman_filter.py     # Filtro de Kalman para estimación de FairPrice y MidPrice
├─ spread.py            # Cálculo avanzado de Spread Óptimo
├─ wallet.py            # Conexión a MetaMask y envío de órdenes
├─ main.py              # Script principal que orquesta todos los módulos
├─ requirements.txt
└─ README.md
```

## EXPLICACIÓN DE LOS MÓDULOS 🧩

## 1️⃣ **API POLYMARKET** (`api_polymarket.py`)
Este módulo gestiona la conexión e interacción con la plataforma Polymarket.

* **Conexión REST API:** Obtiene información inicial de eventos y sub-markets.

```Python
SLUG_MERCADO = re.sub(r"\s+", "-", re.sub(r"[^\w\s]", "", MERCADO.lower())).strip("-")
tokens = elegir_submarket(SLUG_MERCADO)
Conexión WebSocket: Recibe datos del libro de órdenes (bids, asks) en tiempo real.
```

```Python
async with websockets.connect(WS_URL) as websocket:
    await websocket.send(json.dumps({
        "assets_ids": tokens,
        "type": "market"
    }))
```
* **Cálculos base:** Best Bid, Best Ask, MidPrice y Spread.

```Python
mid_price = (best_bid + best_ask) / 2
spread = abs(best_ask - best_bid)
```

## 2️⃣ **FILTRO DE KALMAN** (`kalman_filter.py`)
**Objetivo:** Estimar el **FairPrice** (precio justo) y detectar tendencias de mercado, suavizando la volatilidad del `mid_price` observado.

* **Variables de entrada (Observación):**

```Plaintext
mid_price, best_bid, best_ask, bid_volume, ask_volume, volume_diff
```

* **Matrices del filtro:** Se definen `transition_matrix` (evolución del estado), `observation_matrix` (qué se observa), y las covarianzas de transición y observación (incertidumbre).


* **Salida del filtro (Estimación):**

```Python
df['estimated_price']       # FairPrice estimado
df['estimated_volume_diff'] # Diferencia de volúmenes estimada
Validación de resultados: Se generan gráficas para comparar el precio observado y el estimado.
```
```Python
plt.plot(df['mid_price'], label='Mid Price Observado')
plt.plot(df['estimated_price'], label='Precio Estimado (Kalman)')
plt.legend()
```

## 3️⃣ **SPREAD ÓPTIMO AVANZADO** (`spread.py`)
El módulo implementa un cálculo dinámico del spread que no se limita a un valor fijo.

Se consideran factores clave para maximizar la eficiencia y minimizar el riesgo:

* **Volatilidad del mercado:** spread más amplio en mercados volátiles.

* **Inventario actual:** Ajusta el spread para reequilibrar la posición (vender más rápido en exceso o protegerse).

* **Aversión al riesgo:** Mayor riesgo percibido implica un spread más amplio.

* **Profundidad del libro de órdenes:** Influencia de la liquidez disponible.

* **Cálculo conceptual:**

```Python
spread_optimo = f(volatilidad, inventario, aversion_riesgo, profundidad)
bid_price = fair_price - spread_optimo / 2
ask_price = fair_price + spread_optimo / 2
```

## 4️⃣ **WALLET Y ENVÍO DE ÓRDENES** (`wallet.py`)
Gestiona la interacción con la wallet (simulada o real vía API para MetaMask) para la firma y envío de transacciones.

* **Conexión y envío conceptual:**

```Python
wallet.conectar_metamask()
wallet.enviar_orden(asset_id, price, size, side)
```

* **Funcionalidades:**

   * Conexión segura con la wallet del usuario.

   * Firma de transacciones (órdenes de compra/venta).

   * Registro de órdenes enviadas y estado de ejecución.

   * Control de inventario.

## 5️⃣ **SCRIPT PRINCIPAL** (`main.py`)
El script principal orquesta todos los módulos, encapsulando la lógica en un objeto `MarketMakerBot` basado en POO.

* **Orquestación y flujo:**

```Python
# Inicialización de módulos
market_data = MarketData(SLUG_MERCADO)
kalman = KalmanEstimator(df)
spread_calc = SpreadCalculator()
wallet = WalletConnector()

# Bot de Market Making
bot = MarketMakerBot(market_data, kalman, spread_calc, wallet)
await bot.run()
```

* **Funciones principales del MarketMakerBot:**

   * Obtención de datos en tiempo real.

   * Estimación de FairPrice y tendencias.

   * Cálculo de spread óptimo, ajustando bid y ask.

   * Envío de órdenes al mercado.

   * Control de inventario y riesgos.

Todo el flujo está encapsulado en objetos, facilitando escalabilidad y mantenimiento.

## CONTRIBUCIÓN 🚀
Este proyecto es modular, lo que facilita las siguientes contribuciones:

* Añadir nuevas estrategias de estimación de precio o indicadores de mercado.

* Integrar modelos de riesgo o aversión al riesgo más avanzados.

* Probar otros mercados de Polymarket sin modificar la arquitectura principal.

* Ampliar la conexión de wallets o exchanges adicionales.
