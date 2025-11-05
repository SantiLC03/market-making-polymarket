import numpy as np
import time
#from market_visualizer import MarketDataVisualizer

class KalmanFairPriceEstimator:
    def __init__(self, initial_mid_price, Q=0.09, R=0.04):
        self.F = 1  # Matriz de transición de estado
        self.H = 1  # Matriz de observación
        self.Q = Q  # Varianza del ruido del proceso
        self.R = R  # Varianza del ruido de medición

        # Inicialización del filtro
        self.x = initial_mid_price  # Estimación inicial del fair price
        self.P = 1  # Covarianza inicial del error de estimación

    def update(self, new_bid, new_ask):
        new_mid_price = (new_bid + new_ask) / 2

        # Paso de predicción
        x_pred = self.F * self.x
        P_pred = self.F * self.P * self.F + self.Q

        # Paso de actualización
        K = P_pred * self.H / (self.H * P_pred * self.H + self.R)
        self.x = x_pred + K * (new_mid_price - self.H * x_pred)
        self.P = (1 - K * self.H) * P_pred

        return self.x
