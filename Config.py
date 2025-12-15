# ==============================================================================
# CONFIGURACIÓN GENERAL DEL BOT
# ==============================================================================

# --- Control de Tiempo y Mercado ---
# Duración total de la sesión de trading activa (Fase 3) en segundos.
TIEMPO_TOTAL = 180 

# Velocidad del bot: Cuántos segundos espera entre cada ciclo de análisis.
# 0.5s significa que el bot "piensa" y recalcula 2 veces por segundo.
INTERVALO_TICK = 0.5  

# Identificador único del mercado en Polymarket (se saca de la URL).
# En este caso: Un mercado de Bitcoin (Up/Down) de 15 minutos.
SLUG_MERCADO = "btc updown 15m 1765197000?" 

# --- Gestión de Datos ---
# Tamaño de la ventana para calcular la volatilidad móvil.
# Mira los últimos 20 precios para decidir qué tan "nervioso" está el mercado.
ROLLING_VOL_WINDOW = 20 

# Duración de la Fase 1 (Calentamiento).
# Número de datos que recolecta para calibrar el modelo antes de empezar a operar.
WARMUP_TICKS = 20 

# --- Gestión de Riesgo (Inventario) ---
# Restricción dura de inventario (tipo "Stop Loss" de posición).
# Si el bot alcanza este número (ej: +20 long o -20 short), SE BLOQUEA 
# y deja de operar en esa dirección para no acumular más riesgo.
MAX_INVENTARIO = 20    

# ==============================================================================
# PARÁMETROS DEL MODELO AVELLANEDA-STOIKOV (ESTRATEGIA)
# ==============================================================================

# Aversión al riesgo base (Gamma).
# Controla qué tan rápido el bot entra en pánico cuando tiene inventario.
# - Valor bajo (0.001): Bot tranquilo, aguanta inventario esperando spread.
# - Valor alto (>0.1): Bot nervioso, baja precios agresivamente para vender rápido.
GAMMA_BASE = 0.001 

# Densidad del mercado por defecto (Kappa).
# Se usa SOLO si la calibración automática falla (que suele fallar).
# - Kappa alto: Mercado difícil de mover (mucha liquidez).
# - Kappa bajo: Mercado fácil de mover (poca liquidez).
KAPPA_FALLBACK = 50 

# ==============================================================================
# PARÁMETROS DEL FILTRO DE KALMAN ADAPTATIVO (CEREBRO)
# ==============================================================================

# Valores iniciales para el filtro.
# Al estar en 'None', el bot los calculará matemáticamente (MLE) durante el Warmup.
Q_BASE_DIAG = None # Incertidumbre del modelo (cuánto cambia el precio real).
R_BASE_DIAG = None # Ruido de medición (cuánto miente el precio observado).
SIGMA_BASE = None  # Volatilidad base inicial.

# Multiplicadores de Adaptabilidad Dinámica
# Controlan qué tan sensible es el filtro a los cambios del mercado en vivo.

# Si el spread (diferencia bid-ask) aumenta, R aumenta X veces.
# Efecto: El filtro confía menos en el precio actual (asume más ruido).
R_FACTOR_SPREAD = 50.0 

# Si la volatilidad aumenta, Q aumenta X veces.
# Efecto: El filtro se vuelve más rápido para seguir la nueva tendencia.
Q_FACTOR_VOL = 30.0

# ==============================================================================
# CONFIGURACIÓN DE EJECUCIÓN (REAL vs SIMULACIÓN)
# ==============================================================================

# Interruptor Maestro de Dinero Real
# False = MODO SIMULACIÓN (Juega con dinero ficticio, seguro para pruebas).
# True  = MODO REAL (Conecta a tu Wallet y gasta USDC real).
MODO_REAL = False 

# Tamaño de la apuesta por orden en USDC (Solo afecta si MODO_REAL = True)
# Ejemplo: 1.0 significa que cada orden de compra/venta será de 1 USDC.
SIZE_USDC = 1.0