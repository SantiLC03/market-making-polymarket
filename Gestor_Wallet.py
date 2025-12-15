import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
# Importaciones necesarias para operar
from py_clob_client.clob_types import OrderArgs, OrderType, AssetType, BalanceAllowanceParams
from py_clob_client.constants import POLYGON

# Cargar variables de entorno (Private Key)
load_dotenv()

class GestorWallet:
    """
    Clase encargada de interactuar con la Blockchain (Polygon) y el CLOB de Polymarket.
    Maneja autenticación, balances y ejecución de órdenes reales.
    """
    
    def __init__(self):
        """
        Inicializa la conexión segura.
        Intenta recuperar credenciales existentes para evitar conflictos de API Key.
        """
        self.private_key = os.getenv("PK_POLYMARKET")
        
        if not self.private_key:
            raise ValueError("ERROR CRÍTICO: No se encontró 'PK_POLYMARKET' en el archivo .env")

        print("[WALLET] Conectando a Polymarket (Polygon)...")
        
        # 1. Inicializar cliente con la Private Key
        self.client = ClobClient(
            host="https://clob.polymarket.com/",
            key=self.private_key,
            chain_id=137 # Polygon Mainnet
        )
        
        # 2. Gestión de Credenciales de API (L2)
        try:
            # Intentar recuperar credenciales existentes (evita error 400)
            creds = self.client.derive_api_key()
            print("[WALLET] ✅ Credenciales API recuperadas correctamente.")
        except Exception:
            print("[WALLET] Credenciales no encontradas. Generando nuevas...")
            try:
                # Si no existen, crear nuevas (firma mensaje con la wallet)
                creds = self.client.create_api_key()
                print("[WALLET] ✅ Nuevas credenciales API creadas.")
            except Exception as e:
                print(f"[WALLET] ❌ Error de autenticación: {e}")
                creds = None

        if creds:
            self.client.set_api_creds(creds)
        else:
            raise ConnectionError("No se pudo autenticar con la API de Polymarket.")

    def obtener_balance_usdc(self):
        """Devuelve el balance disponible de USDC en la wallet."""
        try:
            # Usar objeto de parámetros correcto para la librería
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            resp = self.client.get_balance_allowance(params=params)
            
            # El balance viene en unidades 'wei' (6 decimales para USDC)
            balance_raw = float(resp.get('balance', 0))
            return balance_raw / 1_000_000 
            
        except Exception as e:
            print(f"[WALLET] Error leyendo balance: {e}")
            return 0.0

    def cancelar_todas_las_ordenes(self):
        """
        Cancela TODAS las órdenes abiertas en el mercado.
        Útil para limpiar posiciones al inicio o fin de sesión.
        """
        try:
            self.client.cancel_all()
            return True
        except Exception as e:
            # Es normal que falle si no hay órdenes abiertas, no es crítico
            # print(f"[WALLET] Info cancelacion: {e}")
            return False

    def colocar_orden(self, token_id, precio, cantidad_shares, lado):
        """
        Envía una orden LIMIT al libro de órdenes.
        
        :param token_id: ID del activo (YES/NO).
        :param precio: Precio límite (0.01 - 0.99).
        :param cantidad_shares: Número de acciones a comprar/vender.
        :param lado: "BUY" o "SELL".
        """
        try:
            # 1. Validaciones de seguridad
            precio = round(precio, 2) # Polymarket solo acepta 2 decimales
            if precio <= 0 or precio >= 1: 
                return None
            
            if cantidad_shares <= 0:
                return None

            # 2. Configurar tipo de orden
            side_enum = OrderType.BUY if lado.upper() == "BUY" else OrderType.SELL
            
            # 3. Construir payload
            order_args = OrderArgs(
                price=precio,
                size=cantidad_shares,
                side=side_enum,
                token_id=token_id
            )

            # 4. Enviar orden firmada
            resp = self.client.create_and_post_order(order_args)
            
            # 5. Verificar éxito
            if resp and resp.get("success"):
                return resp.get("orderID")
            else:
                print(f"[WALLET] Orden rechazada por el servidor: {resp.get('errorMsg')}")
                return None

        except Exception as e:
            print(f"[WALLET] Excepción crítica al ordenar: {e}")
            return None

# Bloque de prueba (Solo se ejecuta si corres este archivo directamente)
if __name__ == "__main__":
    try:
        gw = GestorWallet()
        bal = gw.obtener_balance_usdc()
        print(f"💰 Balance USDC: {bal}")
        
        # gw.cancelar_todas_las_ordenes() # Descomentar para probar limpieza
    except Exception as e:
        print(f"Error en prueba: {e}")