import numpy as np
from pykalman import KalmanFilter  # Librería optimizada para filtro de Kalman
from scipy.optimize import minimize  # Optimizador numérico para MLE

#################################################################
# 2. Clase KalmanMLECalibrator (Calibrador de Kalman)
#################################################################

class KalmanMLECalibrator:
    """
    Esta clase se utiliza UNA SOLA VEZ al inicio de la sesión (Fase 2).
    Su objetivo es analizar los datos históricos recolectados en el 'Warmup'
    para encontrar la configuración inicial óptima del filtro de Kalman.
    """
    
    def __init__(self, wmp_data, vol_diff_data):
        """
        Inicializa el calibrador con los datos observados.
        
        :param wmp_data: Lista de precios observados (Weighted Mid-Price).
        :param vol_diff_data: Lista de diferencias de volumen (Bid Vol - Ask Vol).
        """
        # Convertir listas a arrays de numpy para eficiencia
        self.wmp_obs = np.array(wmp_data)
        self.vol_diff_obs = np.array(vol_diff_data)
        
        # Apilar las observaciones en una matriz (N muestras x 2 variables)
        self.observations = np.column_stack([self.wmp_obs, self.vol_diff_obs])

        # --- Definición del Modelo de Espacio de Estados ---
        # Estado x = [Precio, Velocidad_Precio, VolDiff, Velocidad_VolDiff]
        
        # Matriz de Transición (F): Cómo evoluciona el estado en el tiempo
        # Asumimos movimiento con velocidad constante: x_t = x_{t-1} + v_{t-1}
        self.transition_matrix = np.array([
            [1, 1, 0, 0], # Precio = Precio_prev + Vel_Precio
            [0, 1, 0, 0], # Vel_Precio = Vel_Precio_prev (constante + ruido)
            [0, 0, 1, 1], # VolDiff = VolDiff_prev + Vel_VolDiff
            [0, 0, 0, 1]  # Vel_VolDiff = Vel_VolDiff_prev
        ])
        
        # Matriz de Observación (H): Qué parte del estado podemos medir directamente
        # Solo medimos el Precio (índice 0) y el VolDiff (índice 2)
        self.observation_matrix = np.array([
            [1, 0, 0, 0], # Observación 1 = Precio
            [0, 0, 1, 0]  # Observación 2 = VolDiff
        ])

    def _log_likelihood(self, params):
        """
        Función de coste que el optimizador intenta minimizar.
        Calcula la probabilidad (Log-Likelihood) de que los datos observados
        hayan sido generados por un filtro de Kalman con los parámetros dados.
        """
        # Desempaquetar los 6 parámetros que estamos optimizando
        # Q (ruido proceso): Precio, Vel_Precio, VolDiff, Vel_VolDiff
        # R (ruido medición): Precio, VolDiff
        Q_p, Q_v, Q_d, Q_s, R_price, R_volume = params
        
        # Construir las matrices de covarianza diagonales
        transition_covariance = np.diag([Q_p, Q_v, Q_d, Q_s]) # Matriz Q
        observation_covariance = np.diag([R_price, R_volume]) # Matriz R

        # Estado inicial estimado (usamos la primera observación como punto de partida)
        initial_state_mean = [self.wmp_obs[0], 0, self.vol_diff_obs[0], 0]
        initial_state_covariance = np.eye(4) * 1.0 # Incertidumbre inicial estándar

        # Crear una instancia temporal del filtro con estos parámetros
        kf = KalmanFilter(
            transition_matrices=self.transition_matrix,
            observation_matrices=self.observation_matrix,
            initial_state_mean=initial_state_mean,
            initial_state_covariance=initial_state_covariance,
            transition_covariance=transition_covariance,
            observation_covariance=observation_covariance
        )
        
        try:
            # Calcular log-likelihood. Devolvemos negativo porque 'minimize' busca el mínimo
            return -kf.loglikelihood(self.observations)
        except (np.linalg.LinAlgError, ValueError):
            # Si los parámetros son matemáticamente inválidos, devolver infinito
            return np.inf

    def fit(self):
        """
        Ejecuta la optimización para encontrar los mejores parámetros Q y R.
        Utiliza el algoritmo L-BFGS-B.
        
        :return: (Q_base_diagonal, R_base_diagonal)
        """
        # Valores iniciales razonables para empezar la búsqueda
        initial_params = [0.01, 0.01, 0.1, 0.1, 0.1, 1.0]
        
        # Restricciones: Todos los valores deben ser positivos (> 0)
        # Usamos 1e-6 como límite inferior para evitar divisiones por cero
        bounds = [(1e-6, None)] * 6

        # Ejecutar optimización
        result = minimize(
            self._log_likelihood, 
            initial_params,
            method='L-BFGS-B', 
            bounds=bounds
        )
        
        # Devolver los resultados separados en dos vectores (diag Q y diag R)
        return result.x[:4], result.x[4:] 
    
    def filter_data(self, Q_diag, R_diag):
        """
        Aplica el filtro de Kalman a los datos históricos usando los parámetros calibrados.
        Útil para calcular la volatilidad histórica suavizada (Sigma Base).
        
        :param Q_diag: Vector diagonal de la matriz Q óptima.
        :param R_diag: Vector diagonal de la matriz R óptima.
        :return: Array con los precios suavizados (Estado 0).
        """
        Q_opt = np.diag(Q_diag)
        R_opt = np.diag(R_diag)
        
        initial_state_mean = [self.wmp_obs[0], 0, self.vol_diff_obs[0], 0]
        
        # Configurar filtro final
        optimal_kf = KalmanFilter(
            transition_matrices=self.transition_matrix,
            observation_matrices=self.observation_matrix,
            initial_state_mean=initial_state_mean,
            initial_state_covariance=np.eye(4),
            transition_covariance=Q_opt,
            observation_covariance=R_opt
        )
        
        # Ejecutar filtrado (smoothing) sobre todo el historial
        states_mean, _ = optimal_kf.filter(self.observations)
        
        # Retornar solo la columna 0 (Precio estimado)
        return states_mean[:, 0]