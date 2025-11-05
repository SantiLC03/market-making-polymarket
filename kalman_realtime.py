import asyncio
import json
import websockets
import requests
import re
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from BasicKalman import KalmanFairPriceEstimator

async def main():
    print("🔍 Buscando mercado del Real Madrid...")
    url = "https://gamma-api.polymarket.com/events?slug=uefa-champions-league-winner"
    #url = "https://gamma-api.polymarket.com/events?slug=when-will-the-government-shutdown-end"
    
    r = requests.get(url)
    
    if r.status_code != 200:
        print(f"❌ Error al acceder a la API: {r.status_code}")
        return
        
    response = r.json()
    if not response:
        print("❌ No se encontró el mercado")
        return
        
    event = response[0]
    print(f"✅ Evento encontrado: {event.get('title')}")
    
    markets = event.get("markets", [])
    if not markets:
        print("❌ No hay mercados disponibles")
        return
        
    market = markets[0]
    print(f"📊 Mercado: {market.get('question')}")
    
    token_ids = json.loads(market.get("clobTokenIds", "[]"))
    print(f"🔑 Token IDs: {token_ids}")
    
    ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    print("\n🔄 Conectando al WebSocket...")
    
    async with websockets.connect(ws_url) as websocket:
        print("✅ Conexión establecida")
        
        await websocket.send(json.dumps({
            "assets_ids": token_ids,
            "type": "market"
        }))
        print("📡 Suscrito al mercado")
        print("\n⏳ Esperando datos iniciales...")
        
        # Esperar por el primer dato real
        initial_bid = None
        initial_ask = None
        while initial_bid is None or initial_ask is None:
            try:
                msg = await websocket.recv()
                if msg == "PONG":
                    continue
                    
                data = json.loads(msg)
                events = data if isinstance(data, list) else [data]
                
                for ev in events:
                    if ev.get("event_type") == "book":
                        bids_data = ev.get("bids", [])
                        asks_data = ev.get("asks", [])
                        
                        if bids_data and asks_data:
                            initial_bid = max([float(b["price"]) for b in bids_data])
                            initial_ask = min([float(a["price"]) for a in asks_data])
                            break
                            
            except Exception as e:
                continue
                
            if initial_bid is not None and initial_ask is not None:
                break
        
        initial_mid = (initial_bid + initial_ask) / 2
        print(f"\n📈 Datos iniciales recibidos:")
        print(f"Bid: {initial_bid:.4f}")
        print(f"Ask: {initial_ask:.4f}")
        print(f"Mid: {initial_mid:.4f}")
        
        print(f"\n🔧 Inicializando Filtro de Kalman con precio medio inicial: {initial_mid:.4f}")
        estimator = KalmanFairPriceEstimator(initial_mid)

        # Configuración de la visualización
        plt.style.use('dark_background')
        plt.ion()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        window_size = 50
        
        # Datos para ambas gráficas
        times = [0]
        bids = [initial_bid]
        asks = [initial_ask]
        mids = [initial_mid]
        fairs = [initial_mid]
        spreads = [initial_ask - initial_bid]
        
        # Gráfica principal de precios
        line_bid, = ax1.plot(times, bids, '--', color='#FFA500', alpha=0.7, label='Bid', linewidth=1)
        line_ask, = ax1.plot(times, asks, '--', color='#00FF00', alpha=0.7, label='Ask', linewidth=1)
        line_mid, = ax1.plot(times, mids, '-', color='#4169E1', alpha=0.8, label='Mid', linewidth=1)
        line_fair, = ax1.plot(times, fairs, '-', color='#FF0000', label='Fair Price', linewidth=2)
        
        ax1.set_title('Precios en tiempo real', color='white', pad=10)
        ax1.set_xlabel('Tiempo')
        ax1.set_ylabel('Precio')
        ax1.grid(True, alpha=0.2)
        ax1.legend(loc='upper left')
        
        # Ajustar los límites iniciales basados en los primeros datos
        price_margin = (initial_ask - initial_bid) * 2
        ax1.set_ylim(min(initial_bid - price_margin, 0), max(initial_ask + price_margin, 1))
        
        # Gráfica de spread
        line_spread, = ax2.plot(times, spreads, '-', color='#BA55D3', label='Spread', linewidth=1)
        ax2.set_xlabel('Tiempo')
        ax2.set_ylabel('Spread')
        ax2.grid(True, alpha=0.2)
        ax2.legend(loc='upper left')
        ax2.set_ylim(0, (initial_ask - initial_bid) * 3)
        
        plt.tight_layout()
        plt.show(block=False)
        
        current_step = 1
        
        print("\n⏳ Iniciando estimación de Fair Price (Ctrl+C para detener)...\n")
        print("     Bid    |    Ask    |    Mid    | Fair Price |   Spread  ")
        print("--------------------------------------------------------")
        
        while True:
            try:
                msg = await websocket.recv()
                
                if msg == "PONG":
                    continue
                    
                try:
                    data = json.loads(msg)
                except:
                    continue
                    
                events = data if isinstance(data, list) else [data]
                
                for ev in events:
                    if ev.get("event_type") == "book":
                        bids_data = ev.get("bids", [])
                        asks_data = ev.get("asks", [])
                        
                        if bids_data and asks_data:
                            best_bid = max([float(b["price"]) for b in bids_data])
                            best_ask = min([float(a["price"]) for a in asks_data])
                            mid_price = (best_bid + best_ask) / 2
                            spread = best_ask - best_bid
                            
                            fair_price = estimator.update(best_bid, best_ask)
                            
                            # Actualizar datos
                            times.append(current_step)
                            bids.append(best_bid)
                            asks.append(best_ask)
                            mids.append(mid_price)
                            fairs.append(fair_price)
                            spreads.append(spread)
                            
                            if len(times) > window_size:
                                times.pop(0)
                                bids.pop(0)
                                asks.pop(0)
                                mids.pop(0)
                                fairs.pop(0)
                                spreads.pop(0)
                            
                            # Actualizar líneas
                            line_bid.set_data(times, bids)
                            line_ask.set_data(times, asks)
                            line_mid.set_data(times, mids)
                            line_fair.set_data(times, fairs)
                            line_spread.set_data(times, spreads)
                            
                            # Ajustar límites
                            ax1.set_xlim(max(0, current_step - window_size), current_step + 5)
                            ax2.set_xlim(max(0, current_step - window_size), current_step + 5)
                            
                            # Ajustar límites del spread dinámicamente
                            if len(spreads) > 0:
                                max_spread = max(spreads) * 1.2
                                ax2.set_ylim(0, max_spread)
                            
                            # Actualizar gráfica
                            fig.canvas.draw()
                            fig.canvas.flush_events()
                            
                            print(f"\r{best_bid:9.4f} | {best_ask:9.4f} | {mid_price:9.4f} | {fair_price:9.4f} | {spread:9.4f}", end="")
                            
                            current_step += 1
                            
            except websockets.exceptions.ConnectionClosed:
                print("\n\n⚠️ Conexión cerrada")
                break
                
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa detenido por el usuario")
        plt.close('all')
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        plt.close('all')