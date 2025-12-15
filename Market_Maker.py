import numpy as np
import matplotlib.pyplot as plt
import time
import asyncio
import json
import pandas as pd
import os
from datetime import datetime
from IPython.display import clear_output, display

# Importaciones de módulos propios
from Rastreador_Polymarket import RastreadorPolymarket
from Kalman_Filter import KalmanMLECalibrator
from Ploteo_vivo import LivePlotter
from Avellaneda import AvellanedaStrategy

# Importación opcional del Gestor de Wallet
try:
    from Gestor_Wallet import GestorWallet
    WALLET_AVAILABLE = True
except ImportError:
    WALLET_AVAILABLE = False

#################################################################
# 3. Función Principal de Market Making Asíncrona
#################################################################

async def ejecutar_sesion_market_maker(params, run_id="RUN", enable_live_plotting=True, save_individual_files=True):
    """
    Ejecuta una sesión completa de market making.
    Se detiene inmediatamente si falla la conexión o NO HAY FONDOS en Modo Real.
    """
    
    # ==============================================================================
    # 1. CARGAR CONFIGURACIÓN
    # ==============================================================================
    
    TIEMPO_TOTAL_EJECUCION = params.get('TIEMPO_TOTAL') 
    INTERVALO_TICK = params.get('INTERVALO_TICK')       
    SLUG_MERCADO = params.get('SLUG_MERCADO')           
    ROLLING_VOL_WINDOW = params.get('ROLLING_VOL_WINDOW') 
    WARMUP_TICKS = params.get('WARMUP_TICKS')           

    GAMMA_BASE = params.get('GAMMA_BASE')               
    MAX_INVENTARIO = params.get('MAX_INVENTARIO')       
    KAPPA_FALLBACK = params.get('KAPPA_FALLBACK', 50.0) 

    Q_BASE_DIAG_PARAM = params.get('Q_BASE_DIAG')       
    R_BASE_DIAG_PARAM = params.get('R_BASE_DIAG')       
    SIGMA_BASE_PARAM = params.get('SIGMA_BASE')         
    
    R_FACTOR_SPREAD = params.get('R_FACTOR_SPREAD')     
    Q_FACTOR_VOL = params.get('Q_FACTOR_VOL')           

    MODO_REAL = params.get('MODO_REAL', False)          
    SIZE_USDC = params.get('SIZE_USDC', 1.0)            
    
    Q_BASE_DIAG = None
    R_BASE_DIAG = None
    SIGMA_BASE = None
    KAPPA_BASE = None 
    kappa_fallback_usado = False 
    
    # ==============================================================================
    # 2. INICIALIZACIÓN Y SEGURIDAD (WALLET)
    # ==============================================================================

    wallet = None
    
    if MODO_REAL:
        print(f"[{run_id}] 🔒 MODO REAL ACTIVADO: Iniciando conexión segura con Wallet...")
        
        # 1. Chequeo de dependencias
        if not WALLET_AVAILABLE:
            raise ImportError("CRÍTICO: 'MODO_REAL' está activado pero no se encuentra 'Gestor_Wallet.py'.")

        # 2. Intento de conexión y CHEQUEO DE FONDOS
        try:
            wallet = GestorWallet()
            balance = wallet.obtener_balance_usdc()
            
            print(f"[{run_id}] ✅ Wallet Conectada. Balance disponible: {balance:.2f} USDC")
            
            # --- VERIFICACIÓN DE FONDOS ---
            if balance < SIZE_USDC:
                raise ValueError(
                    f"FONDOS INSUFICIENTES: Tienes {balance:.2f} USDC, "
                    f"pero se requieren mínimo {SIZE_USDC} USDC para operar. "
                    "El bot se detendrá para evitar errores."
                )

            # Limpieza preventiva solo si hay fondos
            print(f"[{run_id}] Limpiando órdenes antiguas...")
            wallet.cancelar_todas_las_ordenes()
            
        except Exception as e:
            # ¡KILL SWITCH! Si falla conexión o fondos, matamos el proceso.
            raise ConnectionError(f"⛔ DETENCIÓN DE SEGURIDAD: {e}")

    # ==============================================================================
    # 3. CONEXIÓN AL MERCADO
    # ==============================================================================

    F = np.array([[1, 1, 0, 0], [0, 1, 0, 0], [0, 0, 1, 1], [0, 0, 0, 1]]) 
    H = np.array([[1, 0, 0, 0], [0, 0, 1, 0]])                             
    I = np.eye(4)                                                          

    print(f"[{run_id}] Buscando mercado: {SLUG_MERCADO}")
    tracker = RastreadorPolymarket(SLUG_MERCADO) 
    
    if not tracker.obtener_datos_evento(): 
        raise ValueError(f"No se encontró el evento: {SLUG_MERCADO}")
    if not tracker.seleccionar_sub_mercado(0): 
        raise ValueError("No se pudo seleccionar el mercado.")
    
    TOKEN_A_SEGUIR = json.loads(tracker.datos_mercado_seleccionado.get("outcomes", "[]"))[0]
    TOKEN_ID_LARGO = tracker.mapa_tokens.get(TOKEN_A_SEGUIR)
    print(f"[{run_id}] Rastreando el token: '{TOKEN_A_SEGUIR}' (ID: {TOKEN_ID_LARGO})")

    listener_task = asyncio.create_task(tracker.conectar_y_escuchar())
    await asyncio.sleep(3) 
    
    # Inicialización de variables
    current_state_mean = None
    current_state_cov = np.eye(4)
    inventario = 0
    cash = 0.0
    total_pnl = 0.0
    
    trades_bid_colocados = 0
    trades_ask_colocados = 0
    trades_bid_ejecutados = 0
    trades_ask_ejecutados = 0
    
    hist_wmp, hist_vol_diff = [], []
    hist_kalman_p, hist_reserva_p = [], []
    hist_nuestro_bid = [] 
    hist_nuestro_ask = [] 
    hist_inventario, hist_pnl = [], []
    hist_gamma, hist_sigma = [], []
    hist_Q, hist_R = [], []
    hist_kappa = [] 
    
    hist_data = {
        'wmp': hist_wmp, 'kalman_p': hist_kalman_p, 'reserva_p': hist_reserva_p,
        'nuestro_bid': hist_nuestro_bid, 'nuestro_ask': hist_nuestro_ask,
        'inventario': hist_inventario, 'pnl': hist_pnl, 'gamma': hist_gamma,
        'sigma': hist_sigma, 'Q': hist_Q, 'R': hist_R,
        'kappa': hist_kappa 
    }
    
    is_calibrated = False 
    ultimo_wmp_visto = None
    
    while current_state_mean is None:
        wmp = tracker.obtener_wmp_l2(TOKEN_A_SEGUIR)
        if wmp > 0:
            vol_diff = tracker.obtener_volume_diff(TOKEN_A_SEGUIR)
            current_state_mean = np.array([wmp, 0, vol_diff, 0])
            print(f"[{run_id}] Filtro inicializado. Precio: {wmp:.5f}")
        else:
            await asyncio.sleep(0.5)

    # ==============================================================================
    # 4. PREPARACIÓN DE VISUALIZACIÓN
    # ==============================================================================
    plotter = None
    if enable_live_plotting:
        plotter = LivePlotter(WARMUP_TICKS)
    
    start_time_total_sesion = time.time() 
    tiempo_transcurrido_ejecucion = 0 
    
    try:
        # ==============================================================================
        # FASE 1: CALENTAMIENTO
        # ==============================================================================
        print(f"[{run_id}] Fase 1: Calentamiento ({WARMUP_TICKS} ticks)...")
        
        while len(hist_wmp) < WARMUP_TICKS:
            wmp_obs = tracker.obtener_wmp_l2(TOKEN_A_SEGUIR)
            vol_diff_obs = tracker.obtener_volume_diff(TOKEN_A_SEGUIR)
            kappa_estimada_real = tracker.obtener_kappa(TOKEN_A_SEGUIR) 

            if wmp_obs > 0 and wmp_obs != ultimo_wmp_visto:
                if enable_live_plotting:
                    print(f"[{run_id}] CALENTANDO... Tick {len(hist_wmp)+1}/{WARMUP_TICKS} | WMP={wmp_obs:.5f}", end="\r")
                
                hist_wmp.append(wmp_obs)
                hist_vol_diff.append(vol_diff_obs)
                
                hist_kalman_p.append(wmp_obs); hist_reserva_p.append(np.nan)
                hist_nuestro_bid.append(np.nan); hist_nuestro_ask.append(np.nan)
                hist_inventario.append(0); hist_pnl.append(0)
                hist_gamma.append(GAMMA_BASE); hist_sigma.append(0.01)
                hist_Q.append(0); hist_R.append(0)
                hist_kappa.append(kappa_estimada_real)
                
                current_state_mean = F @ current_state_mean 
                current_state_mean[0] = wmp_obs
                current_state_mean[2] = vol_diff_obs
                ultimo_wmp_visto = wmp_obs
            
            await asyncio.sleep(INTERVALO_TICK)

        # ==============================================================================
        # FASE 2: CALIBRACIÓN
        # ==============================================================================
        print(f"\n[{run_id}] Calibrando parámetros...")
        
        if Q_BASE_DIAG_PARAM is None or R_BASE_DIAG_PARAM is None:
            calibrator = KalmanMLECalibrator(hist_wmp, hist_vol_diff)
            Q_BASE_DIAG, R_BASE_DIAG = calibrator.fit()
        else:
            Q_BASE_DIAG, R_BASE_DIAG = Q_BASE_DIAG_PARAM, R_BASE_DIAG_PARAM

        if SIGMA_BASE_PARAM is None:
            if 'calibrator' not in locals():
                calibrator = KalmanMLECalibrator(hist_wmp, hist_vol_diff)
            kalman_prices_warmup = calibrator.filter_data(Q_BASE_DIAG, R_BASE_DIAG)
            SIGMA_BASE = np.std(np.diff(kalman_prices_warmup))
            if SIGMA_BASE == 0: SIGMA_BASE = 0.01
        else:
            SIGMA_BASE = SIGMA_BASE_PARAM
        
        KAPPA_BASE = np.nanmean(hist_kappa) 
        if np.isnan(KAPPA_BASE) or KAPPA_BASE < 1e-4:
            print(f"[{run_id}] Calibración KAPPA fallida. Usando Fallback: {KAPPA_FALLBACK}")
            KAPPA_BASE = KAPPA_FALLBACK
            kappa_fallback_usado = True
        else:
            print(f"[{run_id}] KAPPA_BASE CALIBRADO: {KAPPA_BASE:.4f}")

        hist_sigma = [SIGMA_BASE] * WARMUP_TICKS
        hist_kappa = [KAPPA_BASE] * WARMUP_TICKS
        is_calibrated = True

        avellaneda_strategy = AvellanedaStrategy(
            gamma_base=GAMMA_BASE,
            tiempo_total=TIEMPO_TOTAL_EJECUCION,
            max_inventario=MAX_INVENTARIO
        )

        # ==============================================================================
        # FASE 3: EJECUCIÓN ADAPTATIVA (TRADING LOOP)
        # ==============================================================================
        print(f"[{run_id}] Iniciando Trading por {TIEMPO_TOTAL_EJECUCION}s...")
        start_time_ejecucion = time.time()
        
        while tiempo_transcurrido_ejecucion <= TIEMPO_TOTAL_EJECUCION: 
            tiempo_actual = time.time()
            tiempo_transcurrido_ejecucion = tiempo_actual - start_time_ejecucion
            tiempo_restante = TIEMPO_TOTAL_EJECUCION - tiempo_transcurrido_ejecucion
            
            wmp_obs = tracker.obtener_wmp_l2(TOKEN_A_SEGUIR)
            vol_diff_obs = tracker.obtener_volume_diff(TOKEN_A_SEGUIR)
            best_bid_real = tracker.obtener_mejor_bid(TOKEN_A_SEGUIR)
            best_ask_real = tracker.obtener_mejor_ask(TOKEN_A_SEGUIR)
            z_t = np.array([wmp_obs, vol_diff_obs])
            
            if wmp_obs > 0 and wmp_obs != ultimo_wmp_visto:
                
                # --- A. Kalman Adaptativo ---
                window = min(len(hist_kalman_p), ROLLING_VOL_WINDOW)
                rolling_sigma = np.std(np.diff(hist_kalman_p[-window:]))
                if rolling_sigma == 0: rolling_sigma = SIGMA_BASE
                
                Q_dynamic = np.diag(Q_BASE_DIAG) * (1 + rolling_sigma * Q_FACTOR_VOL)
                spread_mercado = abs(best_ask_real - best_bid_real)
                R_dynamic = np.diag(R_BASE_DIAG) * (1 + spread_mercado * R_FACTOR_SPREAD)

                predicted_state_mean = F @ current_state_mean
                predicted_state_cov = F @ current_state_cov @ F.T + Q_dynamic
                innovation = z_t - H @ predicted_state_mean
                innovation_cov = H @ predicted_state_cov @ H.T + R_dynamic
                kalman_gain = predicted_state_cov @ H.T @ np.linalg.inv(innovation_cov)
                current_state_mean = predicted_state_mean + kalman_gain @ innovation
                current_state_cov = (I - kalman_gain @ H) @ predicted_state_cov
                precio_justo_kalman = current_state_mean[0]
                
                # --- B. Simulación de Ejecución (Solo visual para gráficos) ---
                if not np.isnan(hist_nuestro_bid[-1]):
                    if best_ask_real > 0 and best_ask_real <= hist_nuestro_bid[-1] and inventario < MAX_INVENTARIO:
                        inventario += 1
                        cash -= hist_nuestro_bid[-1]
                        trades_bid_ejecutados += 1
                        
                if not np.isnan(hist_nuestro_ask[-1]):
                    if best_bid_real > 0 and best_bid_real >= hist_nuestro_ask[-1] and inventario > -MAX_INVENTARIO:
                        inventario -= 1
                        cash += hist_nuestro_ask[-1]
                        trades_ask_ejecutados += 1
                
                # --- C. Estrategia Avellaneda ---
                bid_optimo, ask_optimo, precio_reserva, gamma_actual = avellaneda_strategy.calcular_spread_optimo(
                    inventario=inventario,
                    precio_justo_kalman=precio_justo_kalman,
                    kappa=KAPPA_BASE,
                    sigma=rolling_sigma,
                    tiempo_transcurrido=tiempo_transcurrido_ejecucion
                )

                # --- D. ENVÍO DE ÓRDENES REALES ---
                if MODO_REAL and wallet:
                    wallet.cancelar_todas_las_ordenes()
                    
                    if not np.isnan(bid_optimo):
                        size_shares_bid = SIZE_USDC / bid_optimo
                        resp_bid = wallet.colocar_orden(TOKEN_ID_LARGO, bid_optimo, size_shares_bid, "BUY")
                        if resp_bid: trades_bid_colocados += 1
                        
                    if not np.isnan(ask_optimo):
                        size_shares_ask = SIZE_USDC / ask_optimo
                        resp_ask = wallet.colocar_orden(TOKEN_ID_LARGO, ask_optimo, size_shares_ask, "SELL")
                        if resp_ask: trades_ask_colocados += 1
                else:
                    if not np.isnan(bid_optimo): trades_bid_colocados += 1
                    if not np.isnan(ask_optimo): trades_ask_colocados += 1
                
                # --- E. Guardar y Plotear ---
                valor_inventario = inventario * precio_justo_kalman
                total_pnl = cash + valor_inventario
                
                hist_wmp.append(wmp_obs)
                hist_kalman_p.append(precio_justo_kalman)
                hist_reserva_p.append(precio_reserva)
                hist_nuestro_bid.append(bid_optimo)
                hist_nuestro_ask.append(ask_optimo)
                hist_inventario.append(inventario)
                hist_pnl.append(total_pnl)
                hist_gamma.append(gamma_actual)
                hist_sigma.append(rolling_sigma)
                hist_Q.append(Q_dynamic[0,0])
                hist_R.append(R_dynamic[0,0])
                hist_kappa.append(KAPPA_BASE)

                if enable_live_plotting and plotter:
                    hist_data['nuestro_bid'] = hist_nuestro_bid
                    hist_data['nuestro_ask'] = hist_nuestro_ask
                    
                    print(f"[{run_id}] T-{int(tiempo_restante)}s | Inv={inventario} | P&L={total_pnl:+.4f} | K={KAPPA_BASE:.1f}", end="\r")
                    plotter.update(hist_data, inventario, total_pnl, tiempo_restante)
                
                ultimo_wmp_visto = wmp_obs

            await asyncio.sleep(INTERVALO_TICK)

    except KeyboardInterrupt:
        print(f"\n[{run_id}] Detenido por usuario.")
        if MODO_REAL and wallet:
            print(f"[{run_id}] Cancelando órdenes abiertas...")
            wallet.cancelar_todas_las_ordenes()
    
    finally:
        # ==============================================================================
        # 5. CIERRE SEGURO
        # ==============================================================================
        await tracker.detener_escucha()
        await listener_task 
        
        if MODO_REAL and wallet:
            print(f"[{run_id}] 🧹 Limpiando órdenes pendientes en el mercado...")
            wallet.cancelar_todas_las_ordenes()
        
        tiempo_sesion_total = time.time() - start_time_total_sesion
        
        if enable_live_plotting and plotter:
            try: clear_output(wait=True)
            except: pass
            if len(hist_wmp) >= WARMUP_TICKS:
                plotter.update(hist_data, inventario, total_pnl, 0)
        
        print(f"[{run_id}] Sesión Finalizada.")
        print(f"[{run_id}] P&L Estimado: {total_pnl:+.5f} | Inventario Final: {inventario}")

        # Guardado de CSV/PNG
        resultados_finales = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'mercado': SLUG_MERCADO,
            'token_seguido': TOKEN_A_SEGUIR,
            'modo_real': MODO_REAL,
            'pnl_final': round(total_pnl, 5),
            'inventario_final': inventario,
            'cash_final': round(cash, 5), # AÑADIDO: Cash Final
            'kappa_calibrada': round(KAPPA_BASE, 4) if is_calibrated else np.nan,
        }
        
        if save_individual_files:
            print(f"[{run_id}] Guardando datos...")
            try:
                CSV_DIR = "Data/simulacion"
                os.makedirs(CSV_DIR, exist_ok=True)
                df_res = pd.DataFrame([resultados_finales])
                f_path = os.path.join(CSV_DIR, "resultados_manuales.csv")
                df_res.to_csv(f_path, mode='a', header=not os.path.exists(f_path), index=False, sep=';')
                
                if is_calibrated and plotter:
                    PNG_DIR = "Data/png"
                    os.makedirs(PNG_DIR, exist_ok=True)
                    tag = f"K{KAPPA_BASE:.2f}_{datetime.now().strftime('%H%M%S')}"
                    plotter.save(os.path.join(PNG_DIR, f"grafico_{tag}.png"))
                    plotter.close()
            except Exception as e:
                print(f"Error guardando: {e}")

        if plotter: plotter.close()
        return resultados_finales