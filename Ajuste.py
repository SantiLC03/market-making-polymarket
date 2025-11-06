from Data_base import get_trades_table
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt

data = get_trades_table("66281600716773880802753015201294956591448454218578699327801428058257011939378", limit=100)
print(data)


# Cargar tus datos aquí (reemplaza este DataFrame con tus datos reales)
data = pd.DataFrame({
    "precio": [0.600000, 0.300000, 0.982000, 0.530476, 0.310000, 0.340000, 0.610000, 0.044377, 0.350000, 0.730000],
    "volumen": [1.000000, 10.000000, 10.183277, 21.000000, 9.000000, 31.000000, 5.000000, 112.670221, 10.000000, 27.397259]
})

# Clase del filtro de Kalman con ajuste dinámico de R
class KalmanFairPriceEstimator:
    def __init__(self, initial_price, Q=0.001, R=0.1):
        self.F = 1
        self.H = 1
        self.Q = Q
        self.R_base = R
        self.x = initial_price
        self.P = 1

    def update(self, price, size):
        # Predicción
        x_pred = self.F * self.x
        P_pred = self.F * self.P * self.F + self.Q

        # Ajuste dinámico de R según el volumen (con límites)
        max_volume_effect = 10  # Límite superior para el efecto del volumen
        volume_effect = min(size, max_volume_effect)
        adjusted_R = self.R_base / (1 + volume_effect)
        adjusted_R = max(adjusted_R, 0.01)  # Asegurar que R no sea demasiado pequeño

        # Actualización
        K = P_pred * self.H / (self.H * P_pred * self.H + adjusted_R)
        self.x = x_pred + K * (price - self.H * x_pred)
        self.P = (1 - K * self.H) * P_pred

        return self.x

# Función para simular el filtro con parámetros dados
def run_kalman_filter(data, Q, R_base):
    estimator = KalmanFairPriceEstimator(initial_price=data.iloc[0]["precio"], Q=Q, R=R_base)
    fair_prices = []
    for _, row in data.iterrows():
        fair_price = estimator.update(row["precio"], row["volumen"])
        fair_prices.append(fair_price)
    return fair_prices

# Función de error a minimizar (MAE)
def error_function(params, data):
    Q, R_base = params
    fair_prices = run_kalman_filter(data, Q, R_base)
    mae = np.mean(np.abs(np.array(fair_prices) - data["precio"]))
    return mae

# Optimización de parámetros
initial_params = [0.001, 0.1]  # Valores iniciales para Q y R
bounds = [(1e-6, 0.1), (1e-6, 0.1)]  # Limitar Q y R_base a valores más pequeños
result = minimize(error_function, initial_params, args=(data,), method="L-BFGS-B", bounds=bounds)
Q_opt, R_opt = result.x

# Simular el filtro con los parámetros óptimos
fair_prices_opt = run_kalman_filter(data, Q_opt, R_opt)

# Visualización
plt.figure(figsize=(12, 6))
plt.plot(data.index, data["precio"], label="Precio Observado", marker='o')
plt.plot(data.index, fair_prices_opt, label=f"Fair Price (Q={Q_opt:.6f}, R={R_opt:.6f})", marker='x')
plt.xlabel("Índice de Trade")
plt.ylabel("Precio")
plt.title("Comparación entre Precio Observado y Fair Price (Kalman)")
plt.legend()
plt.grid(True)
plt.show()

print(f"Parámetros óptimos: Q = {Q_opt:.6f}, R_base = {R_opt:.6f}")
print("Fair Prices calculados:", fair_prices_opt)
