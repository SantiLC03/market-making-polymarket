import numpy as np
import time

class KalmanFairPriceEstimator:
    def __init__(self, initial_mid_price, Q=0.1, R=0.06):
        self.F = 1  # Matriz de transición de estado
        self.H = 1  # Matriz de observación
        self.Q = Q  # Varianza del ruido del proceso
        self.R = R  # Varianza del ruido de medición

        # Inicialización del filtro
        self.x = initial_mid_price  # Estimación inicial del fair price
        self.P = 0.01  # Covarianza inicial del error de estimación

    def update(self, new_bid, new_ask, price, size):
        new_mid_price = (new_bid + new_ask) / 2

        # Paso de predicción
        x_pred = self.F * self.x
        P_pred = self.F * self.P * self.F + self.Q

        # Ajustar R dinámicamente según el volumen del trade
        # Aquí puedes usar una función inversa, por ejemplo: R = R_base / (1 + size)
        # O normalizar el tamaño para evitar valores extremos
        adjusted_R = self.R / (1 + np.log(1 + size))

        # Paso de actualización
        K = P_pred * self.H / (self.H * P_pred * self.H + adjusted_R)
        self.x = x_pred + K * (price - self.H * x_pred)
        self.P = (1 - K * self.H) * P_pred

        return self.x
