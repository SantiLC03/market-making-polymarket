import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, clear_output

#################################################################
# 5. Clase LivePlotter (Visualización en Tiempo Real)
#################################################################

class LivePlotter:
    """
    Clase encargada de gestionar y actualizar los gráficos en tiempo real
    dentro de un entorno Jupyter Notebook.
    """
    
    def __init__(self, warmup_ticks):
        """
        Inicializa el plotter configurando la figura y los ejes.
        
        :param warmup_ticks: Número de ticks de calentamiento para sombrear en el gráfico.
        """
        self.warmup_ticks = warmup_ticks
        
        # Crear la figura y los 3 subplots verticales
        # sharex=True para que al hacer zoom en uno, se muevan todos
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(
            3, 1, 
            figsize=(16, 12), 
            sharex=True, 
            gridspec_kw={'height_ratios': [3, 1, 1]} # El gráfico de precios es más alto
        )
        
        # Ajustar espaciado
        plt.subplots_adjust(hspace=0.1)

    def update(self, hist_data, inventario_final, pnl_final, tiempo_restante, save_only=False):
        """
        Actualiza los datos de los gráficos y refresca la visualización.
        
        :param hist_data: Diccionario con todas las listas de datos históricos.
        :param inventario_final: Valor actual del inventario (q).
        :param pnl_final: Valor actual del P&L.
        :param tiempo_restante: Segundos restantes de la sesión.
        :param save_only: Si True, no borra la salida (útil para guardar el PNG final).
        """
        
        # --- 1. Extracción de datos del diccionario ---
        hist_wmp = hist_data['wmp']
        hist_kalman_p = hist_data['kalman_p']
        hist_reserva_p = hist_data['reserva_p']
        hist_nuestro_bid = hist_data['nuestro_bid']
        hist_nuestro_ask = hist_data['nuestro_ask']
        hist_inventario = hist_data['inventario']
        hist_pnl = hist_data['pnl']

        # --- 2. Limpieza de ejes ---
        # Si estamos en modo en vivo, limpiamos la salida de la celda anterior
        if not save_only:
            clear_output(wait=True)
            
        # Limpiamos el contenido anterior de los ejes para redibujar
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()

        # --- 3. Redibujado de Gráficos ---

        # === GRÁFICO 1: PRECIOS Y ÓRDENES ===
        # Precio de mercado (WMP)
        self.ax1.plot(hist_wmp, label='WMP Observado ($z_t$)', color='gray', linestyle=':', alpha=0.6)
        # Precio Justo (Kalman)
        self.ax1.plot(hist_kalman_p, label='Precio Justo ($S_t$)', color='blue', linewidth=2, alpha=0.8)
        # Precio de Reserva (Avellaneda)
        self.ax1.plot(hist_reserva_p, label='Precio Reserva ($r$)', color='orange', linestyle='--', linewidth=2)
        
        # Nuestras Órdenes (Bid y Ask)
        self.ax1.plot(hist_nuestro_bid, label='Nuestro Bid ($P_b$)', color='green', alpha=0.7)
        self.ax1.plot(hist_nuestro_ask, label='Nuestro Ask ($P_a$)', color='red', alpha=0.7)
        
        # Configuración visual Gráfico 1
        self.ax1.set_title(f"Market Making | Inventario: {inventario_final} | P&L: {pnl_final:+.4f} | Tiempo: {int(tiempo_restante)}s")
        self.ax1.legend(loc='upper left')
        self.ax1.grid(True, linestyle='--', alpha=0.3)
        # Sombrear zona de calentamiento
        self.ax1.axvspan(0, self.warmup_ticks, color='grey', alpha=0.1, label='Warmup')

        # === GRÁFICO 2: GESTIÓN DE INVENTARIO ===
        # Línea de inventario tipo 'step' (escalones)
        self.ax2.plot(hist_inventario, label='Inventario ($q_t$)', color='brown', linewidth=2, drawstyle='steps-post')
        
        # Configuración visual Gráfico 2
        self.ax2.set_title("Evolución del Inventario ($q$)")
        self.ax2.legend(loc='upper left')
        self.ax2.grid(True, linestyle='--', alpha=0.3)
        self.ax2.axhline(0, color='black', linestyle='--', linewidth=1) # Línea cero
        self.ax2.axvspan(0, self.warmup_ticks, color='grey', alpha=0.1)
        
        # Ajuste dinámico del límite Y para que siempre se vea bien el inventario
        max_inv_abs = max(np.max(np.abs(hist_inventario)) if len(hist_inventario) > 0 else 2, 2)
        self.ax2.set_ylim(-max_inv_abs - 1, max_inv_abs + 1)

        # === GRÁFICO 3: RENDIMIENTO (P&L) ===
        self.ax3.plot(hist_pnl, label='P&L Total (Cash + Valor Latente)', color='purple', linewidth=2)
        
        # Configuración visual Gráfico 3
        self.ax3.set_title("Ganancias y Pérdidas (P&L)")
        self.ax3.legend(loc='upper left')
        self.ax3.grid(True, linestyle='--', alpha=0.3)
        self.ax3.axhline(0, color='black', linestyle='--', linewidth=1)
        self.ax3.axvspan(0, self.warmup_ticks, color='grey', alpha=0.1)
        self.ax3.set_xlabel("Número de Ticks (tiempo)")

        # --- 4. Mostrar Figura ---
        if not save_only:
            display(self.fig)
            
    def close(self):
        """Cierra la figura para liberar memoria."""
        plt.close(self.fig)
    
    def save(self, filename):
        """Guarda el gráfico actual en un archivo."""
        self.fig.savefig(filename)