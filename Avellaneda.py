import numpy as np

#################################################################
# 4. Clase de Estrategia Avellaneda-Stoikov
#################################################################

class AvellanedaStrategy:
    def __init__(self, gamma_base, tiempo_total, max_inventario):
        """
        Inicializa la estrategia con los parámetros de riesgo y tiempo.
        
        :param gamma_base: Aversión al riesgo base.
        :param tiempo_total: Duración total de la sesión (para el horizonte de tiempo).
        :param max_inventario: Límite de inventario para frenar operaciones.
        """
        self.gamma_base = gamma_base
        self.tiempo_total = tiempo_total
        self.max_inventario = max_inventario

    def calcular_spread_optimo(self, inventario, precio_justo_kalman, kappa, sigma, tiempo_transcurrido):
        """
        Calcula el precio de reserva y el spread óptimo para una sola capa.
        
        :param inventario: Inventario actual (q).
        :param precio_justo_kalman: Precio estimado por el filtro (S).
        :param kappa: Densidad del mercado calibrada (k).
        :param sigma: Volatilidad rodante actual (sigma).
        :param tiempo_transcurrido: Tiempo desde el inicio de la fase 3.
        """
        
        # 1. Calcular el horizonte de tiempo (T - t) normalizado
        # Se usa max(..., 0.001) para evitar división por cero al final de la sesión
        T_t = max((self.tiempo_total - tiempo_transcurrido) / self.tiempo_total, 0.001) 
        
        # 2. Calcular gamma dinámico (aversión al riesgo)
        # Aumenta exponencialmente si acumulamos mucho inventario
        gamma_actual = self.gamma_base * np.exp(0.1 * abs(inventario))
        
        # 3. Calcular penalización de inventario (Reservation Price Skew)
        # Nota: Usamos sigma^2 (varianza) conforme a la fórmula clásica
        penalizacion = inventario * gamma_actual * (sigma**2) * T_t
        
        # 4. Calcular Precio de Reserva (r)
        precio_reserva = precio_justo_kalman - penalizacion
        
        # 5. Calcular Spread Óptimo (delta)
        # Basado en la liquidez (kappa) y volatilidad (sigma)
        spread_base = (1 / gamma_actual) * np.log(1 + gamma_actual / kappa) * (1 + sigma)
        
        # 6. Calcular Precios Finales (Bid / Ask)
        bid_optimo = precio_reserva - (spread_base / 2)
        ask_optimo = precio_reserva + (spread_base / 2)
        
        # 7. Aplicar "Kill Switch" por Inventario Máximo
        if inventario >= self.max_inventario:
            bid_optimo = np.nan  # Inventario lleno (Long): Dejar de comprar
            
        if inventario <= -self.max_inventario:
            ask_optimo = np.nan  # Inventario lleno (Short): Dejar de vender

        return bid_optimo, ask_optimo, precio_reserva, gamma_actual