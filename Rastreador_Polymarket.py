import re
import json
import requests
import asyncio
import websockets
from datetime import datetime, timedelta
import numpy as np
from scipy.optimize import curve_fit

class RastreadorPolymarket:
    def __init__(self, nombre_mercado):
        """
        Inicializa el rastreador con el nombre del mercado que queremos seguir.
        Configura las URLs de la API y el WebSocket de Polymarket.
        """
        self.nombre_mercado = nombre_mercado
        # Convierte el nombre legible en un 'slug' para la URL (ej: "Will Trump win?" -> "will-trump-win")
        self.slug_mercado = self._generar_slug(nombre_mercado)
        
        # Endpoints de Polymarket
        self.api_url = f"https://gamma-api.polymarket.com/events?slug={self.slug_mercado}"
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        
        # Almacenamiento de datos
        self.datos_evento = None
        self.sub_mercados = []
        self.datos_mercado_seleccionado = None
        self.ids_tokens = [] # IDs de los activos (Yes/No)
        self.mapa_tokens = {} # Mapeo ID -> Nombre
        self.mapa_tokens_inverso = {} # Mapeo Nombre -> ID
        
        # Estado del mercado en tiempo real
        self.libro_ordenes = {} # Almacena bids y asks crudos
        self.precios_actuales = {} # Almacena métricas calculadas (WMP, Kappa, etc.)
        
        # Control del WebSocket
        self.websocket = None
        self.esta_corriendo = False
        self.ultimo_pong = None

    def _generar_slug(self, texto):
        """Convierte texto normal en formato URL-slug."""
        return re.sub(r"\s+", "-", re.sub(r"[^\w\s]", "", texto.lower())).strip("-")

    # ==============================================================================
    # SECCIÓN: CÁLCULOS MATEMÁTICOS (KAPPA)
    # ==============================================================================

    def _exp_decay(self, p, A, k):
        """
        Función matemática de decaimiento exponencial: V(p) = A * exp(-k * p).
        Se usa para modelar cómo disminuye la liquidez a medida que nos alejamos del precio actual.
        """
        return A * np.exp(-k * p)

    def _estimar_kappa(self, bids, asks, mejor_bid, mejor_ask):
        """
        Intenta calcular KAPPA (k), que representa la 'densidad' o 'resistencia' del libro de órdenes.
        Un Kappa alto significa que la liquidez cae rápido (mercado delgado).
        Un Kappa bajo significa que hay mucha liquidez distribuida (mercado profundo).
        
        Utiliza 'curve_fit' para ajustar los datos reales a la función exponencial.
        Devuelve np.nan si no hay suficientes datos o el ajuste falla.
        """
        if not bids or not asks:
            return np.nan

        try:
            # 1. Preparar datos de Venta (Asks)
            # Calculamos la distancia (delta) desde el mejor precio
            ask_prices = np.array([float(a['price']) for a in asks])
            ask_sizes = np.array([float(a['size']) for a in asks])
            ask_deltas = ask_prices - mejor_ask 

            # 2. Preparar datos de Compra (Bids)
            bid_prices = np.array([float(b['price']) for b in bids])
            bid_sizes = np.array([float(b['size']) for b in bids])
            bid_deltas = mejor_bid - bid_prices 

            # 3. Juntar todos los datos
            x_data = np.concatenate((bid_deltas, ask_deltas)) # Distancias
            y_data = np.concatenate((bid_sizes, ask_sizes))   # Volúmenes

            # 4. Filtrar datos ruidosos
            # Ignoramos órdenes con volumen 0 o que están demasiado pegadas al spread (ruido)
            valid_indices = (x_data > 0.005) & (y_data > 0) 
            if np.sum(valid_indices) < 2:
                return np.nan 

            x_fit = x_data[valid_indices]
            y_fit = y_data[valid_indices]

            # 5. Ajuste de Curva (Curve Fitting)
            # Intentamos encontrar los valores A y k que mejor se ajustan a los datos
            p0 = [y_fit[0], 1.0] # Valores iniciales estimados
            bounds = ([0, 0], [np.inf, np.inf]) # Límites (no pueden ser negativos)
            
            popt, _ = curve_fit(self._exp_decay, x_fit, y_fit, p0=p0, maxfev=2000, bounds=bounds)
            
            kappa_estimada = popt[1] # El segundo parámetro es k (Kappa)
            
            if kappa_estimada < 1e-4: # Si es demasiado pequeño, es un error de cálculo
                return np.nan
                
            return kappa_estimada

        except (RuntimeError, ValueError):
            return np.nan

    # ==============================================================================
    # SECCIÓN: PROCESAMIENTO DE DATOS EN TIEMPO REAL
    # ==============================================================================

    def _actualizar_precios_rt(self, asset_id):
        """
        Se llama cada vez que llega un mensaje del WebSocket.
        Recalcula WMP, Volume Diff y Kappa con los nuevos datos del libro.
        """
        if asset_id not in self.libro_ordenes: return
        
        # Obtener listas de órdenes
        bids = self.libro_ordenes[asset_id].get("bids", [])
        asks = self.libro_ordenes[asset_id].get("asks", [])
        
        # Mejores precios disponibles (Top of Book)
        mejor_bid = max([float(b["price"]) for b in bids]) if bids else 0
        mejor_ask = min([float(a["price"]) for a in asks]) if asks else 0
        
        # 1. Calcular KAPPA
        kappa_estimada = self._estimar_kappa(bids, asks, mejor_bid, mejor_ask)
        
        # 2. Calcular WMP (Weighted Mid-Price)
        # Es un precio medio que se inclina hacia donde hay más volumen (presión)
        vol_total_bid = sum([float(b.get("size", 0)) for b in bids])
        vol_total_ask = sum([float(a.get("size", 0)) for a in asks])
        vol_diff = vol_total_bid - vol_total_ask # Diferencia de presión
        
        if (vol_total_bid + vol_total_ask) > 0:
            # Fórmula de Microestructura: WMP = (Bid * Vol_Ask + Ask * Vol_Bid) / Vol_Total
            # Nota: Se cruzan los volúmenes (Vol_Ask pesa al Bid y viceversa)
            wmp = (mejor_bid * vol_total_ask + mejor_ask * vol_total_bid) / (vol_total_bid + vol_total_ask)
        else:
            # Fallback a precio medio simple si no hay volumen
            wmp = (mejor_bid + mejor_ask) / 2

        nombre_resultado = self.mapa_tokens_inverso.get(asset_id, asset_id)
        
        # Guardar resultados
        self.precios_actuales[nombre_resultado] = {
            "mejor_bid": mejor_bid,
            "mejor_ask": mejor_ask,
            "wmp_l2": wmp,
            "volume_diff": vol_diff,
            "total_bid_vol": vol_total_bid, 
            "total_ask_vol": vol_total_ask,
            "kappa": kappa_estimada
        }

    def _procesar_mensaje_ws(self, data):
        """Parsea los mensajes JSON crudos que llegan del WebSocket."""
        eventos = data if isinstance(data, list) else [data]
        for ev in eventos:
            if ev.get("event_type") == "book": # Solo nos interesan actualizaciones del libro
                asset_id = ev.get("asset_id")
                # Actualizamos el libro local
                self.libro_ordenes[asset_id] = {"bids": ev.get("bids", []), "asks": ev.get("asks", [])}
                # Disparamos el recálculo de métricas
                self._actualizar_precios_rt(asset_id)

    # ==============================================================================
    # SECCIÓN: CONEXIÓN Y GESTIÓN (API REST)
    # ==============================================================================

    def obtener_datos_evento(self):
        """Consulta la API de Polymarket para obtener detalles del mercado."""
        try:
            r = requests.get(self.api_url)
            r.raise_for_status()
            respuesta = r.json()
            if not respuesta: return False
            
            self.datos_evento = respuesta[0]
            self.sub_mercados = self.datos_evento.get("markets", [])
            print(f"✅ Evento encontrado: {self.datos_evento.get('title', 'N/A')}")
            return True
        except requests.RequestException:
            return False

    def seleccionar_sub_mercado(self, indice_mercado):
        """Elige uno de los sub-mercados (ej: un partido específico dentro de una liga)."""
        if not (0 <= indice_mercado < len(self.sub_mercados)): return False
        
        self.datos_mercado_seleccionado = self.sub_mercados[indice_mercado]
        # Extraer IDs de los tokens (activos) que se negocian
        self.ids_tokens = json.loads(self.datos_mercado_seleccionado.get("clobTokenIds", "[]"))
        resultados = json.loads(self.datos_mercado_seleccionado.get("outcomes", "[]"))
        
        # Crear diccionarios para traducir IDs <-> Nombres
        self.mapa_tokens = dict(zip(resultados, self.ids_tokens))
        self.mapa_tokens_inverso = dict(zip(self.ids_tokens, resultados))
        
        print(f"\n✔️ Has elegido: {self.datos_mercado_seleccionado.get('question')}")
        print(f"Resultados posibles: {resultados}")
        return True

    # ==============================================================================
    # SECCIÓN: BUCLE ASÍNCRONO (WEBSOCKET)
    # ==============================================================================

    async def conectar_y_escuchar(self):
        """Bucle principal asíncrono que mantiene la conexión viva."""
        if not self.ids_tokens: return
        self.esta_corriendo = True
        self.ultimo_pong = datetime.now()
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.websocket = websocket
                # Suscribirse a los activos seleccionados
                await websocket.send(json.dumps({"assets_ids": self.ids_tokens, "type": "market"}))
                print("\n🎧 Conectado al WebSocket. Escuchando precios...\n")
                
                while self.esta_corriendo:
                    try:
                        # Esperar mensaje con timeout para poder enviar PINGs
                        msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        
                        if msg == "PONG": 
                            self.ultimo_pong = datetime.now()
                            continue
                        
                        try: 
                            self._procesar_mensaje_ws(json.loads(msg))
                        except json.JSONDecodeError: 
                            continue
                            
                    except asyncio.TimeoutError:
                        # Si no hay mensajes en 5s, enviar PING para mantener conexión
                        if self.ultimo_pong + timedelta(seconds=10) < datetime.now(): 
                            await websocket.send("PING")
                    except websockets.exceptions.ConnectionClosed: 
                        break
        except Exception as e:
            print(f"💥 Error en el WebSocket: {e}")
        finally:
            self.esta_corriendo = False
            self.websocket = None
            print("🛑 Rastreador detenido.")

    async def detener_escucha(self):
        """Cierra la conexión ordenadamente."""
        self.esta_corriendo = False
        if self.websocket: await self.websocket.close()

    # ==============================================================================
    # SECCIÓN: GETTERS (ACCESO A DATOS)
    # ==============================================================================
    # Estos métodos permiten a otros scripts obtener los datos calculados de forma segura

    def obtener_wmp_l2(self, n="Yes"): return self.precios_actuales.get(n, {}).get("wmp_l2", 0)
    def obtener_volume_diff(self, n="Yes"): return self.precios_actuales.get(n, {}).get("volume_diff", 0)
    def obtener_mejor_bid(self, n="Yes"): return self.precios_actuales.get(n, {}).get("mejor_bid", 0)
    def obtener_mejor_ask(self, n="Yes"): return self.precios_actuales.get(n, {}).get("mejor_ask", 0)
    def obtener_total_bid_vol(self, n="Yes"): return self.precios_actuales.get(n, {}).get("total_bid_vol", 0)
    def obtener_total_ask_vol(self, n="Yes"): return self.precios_actuales.get(n, {}).get("total_ask_vol", 0)
    
    def obtener_kappa(self, n="Yes"): 
        return self.precios_actuales.get(n, {}).get("kappa", np.nan)