import matplotlib.pyplot as plt

class KalmanIAFairPriceEstimator:
    def __init__(self, initial_mid_price, Q=0.00001, R=0.5):
        self.F = 1  # Matriz de transición de estado
        self.H = 1  # Matriz de observación
        self.Q = Q  # Varianza del ruido del proceso
        self.R_base = R  # Varianza base del ruido de medición
        self.x = initial_mid_price  # Estimación inicial del fair price
        self.P = 0.01  # Covarianza inicial del error de estimación

    def update(self, new_bid, new_ask, price, size):
        new_mid_price = (new_bid + new_ask) / 2

        # Validar que el precio del trade no sea un valor atípico
        if abs(price - new_mid_price) > 3 * (new_ask - new_bid):
            price = new_mid_price  # Usar el mid price si el trade es un valor atípico

        # Paso de predicción
        x_pred = self.F * self.x
        P_pred = self.F * self.P * self.F + self.Q

        # Ajustar R dinámicamente según el volumen del trade, con límites
        max_volume_effect = 10  # Límite superior para el efecto del volumen
        volume_effect = min(size, max_volume_effect)
        adjusted_R = self.R_base / (1 + volume_effect)
        adjusted_R = max(adjusted_R, 0.01)  # Asegurar que R no sea demasiado pequeño

        # Paso de actualización
        K = P_pred * self.H / (self.H * P_pred * self.H + adjusted_R)
        self.x = x_pred + K * (price - self.H * x_pred)
        self.P = (1 - K * self.H) * P_pred

        return self.x

# Ejemplo de uso con visualización

# Simulación de datos de ejemplo
trades = [
    (0.007, 0.01, 0.029, 395.17),
    (0.007, 0.01, 0.001, 63793.36),
    (0.007, 0.01, 0.014, 178.86),
    (0.007, 0.01, 0.001, 63153.36),  # Valor atípico
    (0.007, 0.01, 0.01, 2050.00)
]

estimator = KalmanIAFairPriceEstimator(initial_mid_price=0.0085)


# Almacenar los precios para la gráfica
mid_prices = []
bid_prices = []
ask_prices = []
fair_prices = []

for bid, ask, price, size in trades:
    mid_price = (bid + ask) / 2
    fair_price = estimator.update(bid, ask, price, size)

    mid_prices.append(mid_price)
    bid_prices.append(bid)
    ask_prices.append(ask)
    fair_prices.append(fair_price)

# Graficar
plt.figure(figsize=(12, 6))
plt.plot(mid_prices, label='Mid Price', marker='o')
plt.plot(bid_prices, label='Bid Price', marker='x')
plt.plot(ask_prices, label='Ask Price', marker='x')
plt.plot(fair_prices, label='Fair Price (Kalman)', marker='*')
plt.xlabel('Trade Index')
plt.ylabel('Price')
plt.title('Comparison of Bid, Ask, Mid, and Fair Price (Kalman)')
plt.legend()
plt.grid(True)
plt.show()
