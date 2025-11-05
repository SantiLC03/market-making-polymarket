import numpy as np

class KalmanFairPriceEstimator:
    def __init__(self, initial_mid_price):
        self.F = 1  # Matriz de transición de estado
        self.H = 1  # Matriz de observación
        
        # Ajustamos los parámetros para mayor estabilidad
        self.Q = 0.00001  # Varianza del ruido del proceso - más pequeña para mayor estabilidad
        self.R = 0.0001   # Varianza del ruido de medición - mayor peso a las observaciones
        
        # Inicialización del filtro
        self.x = initial_mid_price
        self.P = 0.01
        
        # Para seguimiento del mercado
        self.last_mid = initial_mid_price
        self.last_fair = initial_mid_price

    def update(self, new_bid, new_ask):
        new_mid_price = (new_bid + new_ask) / 2
        
        # Paso de predicción
        x_pred = self.F * self.x
        P_pred = self.F * self.P * self.F + self.Q

        # Paso de actualización
        K = P_pred * self.H / (self.H * P_pred * self.H + self.R)
        raw_estimate = x_pred + K * (new_mid_price - self.H * x_pred)
        self.P = (1 - K * self.H) * P_pred

        # Calculamos un fair price preliminar
        # Usamos una media móvil exponencial para suavizar
        alpha = 0.3  # Factor de suavizado
        smooth_estimate = alpha * raw_estimate + (1 - alpha) * self.last_fair
        
        # Aseguramos que el precio esté dentro del spread, pero de manera suave
        # Si está fuera, lo acercamos gradualmente
        if smooth_estimate > new_ask:
            self.x = new_ask - (new_ask - new_bid) * 0.1  # Ligeramente por debajo del ask
        elif smooth_estimate < new_bid:
            self.x = new_bid + (new_ask - new_bid) * 0.1  # Ligeramente por encima del bid
        else:
            self.x = smooth_estimate
            
        self.last_fair = self.x
        self.last_mid = new_mid_price
        
        return self.x