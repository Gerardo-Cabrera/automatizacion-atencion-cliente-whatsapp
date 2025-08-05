from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings
import re
import os
import httpx
from typing import Dict, Optional, List
import logging
import uuid
from functools import wraps
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

# Configuración exclusiva desde .env
class Settings(BaseSettings):
    api_pedidos_url: str
    whatsapp_api_url: str
    whatsapp_token: str
    cache_timeout: int = 300
    debug_mode: bool = False
    max_retries: int = 3
    request_timeout: float = 10.0

    @field_validator('api_pedidos_url', 'whatsapp_api_url')
    @classmethod
    def validate_urls(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL debe comenzar con http:// o https://')
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

# Inicializar configuración SIN valores por defecto para URLs/tokens
settings = Settings()

# Configuración de logging mejorada
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Filtro de lenguaje mejorado
PALABRAS_PROHIBIDAS = {
    "estupido", "idiota", "imbecil", "tonto", "pendejo", "pendeja",
    "hijo de puta", "hija de puta", "puta", "cabrón", "cabrona"
}
PROHIBIDAS_REGEX = re.compile(rf"({'|'.join(PALABRAS_PROHIBIDAS)})", re.IGNORECASE)

# Modelos Pydantic mejorados
class PedidoResponse(BaseModel):
    codigo: str
    estado: str
    fecha: str
    producto: str
    cliente: str
    precio_total: str

class WhatsAppMessage(BaseModel):
    from_num: str
    text: str
    
    @field_validator('from_num')
    @classmethod
    def validate_phone(cls, v):
        # Validar formato de número de teléfono
        if not re.match(r'^\d{10,15}$', v.replace('+', '')):
            raise ValueError('Número de teléfono inválido')
        return v

class WebhookRequest(BaseModel):
    entry: List[Dict]
    
    @field_validator('entry')
    @classmethod
    def validate_entry(cls, v):
        if not v:
            raise ValueError('Entry no puede estar vacío')
        return v

# Caché mejorado con TTL
class CacheManager:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        self.cache[key] = (value, datetime.now())
    
    def clear_expired(self):
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= timedelta(seconds=self.ttl)
        ]
        for key in expired_keys:
            del self.cache[key]

pedidos_cache = CacheManager(settings.cache_timeout)

# Decorador mejorado para manejo de errores
def manejar_errores_api(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        for attempt in range(settings.max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
                if e.response.status_code == 404:
                    return None
                if attempt == settings.max_retries - 1:
                    return None
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except httpx.RequestError as e:
                logger.error(f"Error de conexión: {str(e)}")
                if attempt == settings.max_retries - 1:
                    return None
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Error inesperado: {str(e)}")
                return None
        return None
    return wrapper

@manejar_errores_api
async def consultar_pedido_api(codigo: str, user_id: str) -> Optional[PedidoResponse]:
    """Consulta la API externa de pedidos usando URL de .env"""
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        headers = {
            "X-Request-ID": str(uuid.uuid4()),
            "User-Agent": "WhatsApp-Bot/1.0.0"
        }
        
        # Obtener TODOS los pedidos
        response = await client.get(
            settings.api_pedidos_url,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        # Convertir user_id a entero si es necesario
        try:
            user_id_int = int(user_id)
        except ValueError:
            user_id_int = None
        
        # Buscar en la estructura anidada
        for usuario in data.get("pedidos", []):
            # Coincidencia por user_id (entero o string)
            if (usuario.get("user_id") == user_id_int or 
                str(usuario.get("user_id")) == user_id):
                
                for pedido in usuario.get("datos_pedido", []):
                    # Coincidencia por código de pedido
                    if (str(pedido.get("id_pedido")) == codigo or 
                        pedido.get("codigo") == codigo):

                        # Obtener nombres de productos
                        productos = ", ".join(
                            [item["producto"] for item in pedido.get("items", [])]
                        )
                        
                        return PedidoResponse(
                            codigo=str(pedido.get("codigo", pedido.get("id_pedido", ""))),
                            estado=pedido.get("estado"),
                            fecha=pedido.get("fecha", pedido.get("fechaActualizacion", "")),
                            producto=productos,
                            cliente=pedido.get("cliente", ""),
                            precio_total=str(pedido.get("precio_total_pedido", pedido.get("precio_total", ""))) + " USD"
                        )
        return None

async def consultar_pedido(codigo: str, user_id: str) -> Optional[PedidoResponse]:
    """Consulta un pedido con caché mejorado"""
    cache_key = f"{user_id}:{codigo}"
    if cached := pedidos_cache.get(cache_key):
        return cached
    
    # Solo si no está en caché, llamar a la API
    pedido = await consultar_pedido_api(codigo, user_id)
    if pedido:
        pedidos_cache.set(cache_key, pedido)
    
    return pedido


# --- Seguridad: función para sanitizar texto (básica, puede ampliarse) ---
def sanitizar_texto(texto: str) -> str:
    return texto.strip()


LENGUAJE_INAPROPIADO_MSG = (
    "⚠️ *Lenguaje inapropiado detectado*\n\n"
    "Por favor mantén un tono respetuoso.\n"
    "Estoy aquí para ayudarte con tu pedido."
)

def contiene_lenguaje_inapropiado(texto: str) -> str | None:
    """Devuelve el mensaje de advertencia si el texto contiene lenguaje inapropiado, si no None"""
    if PROHIBIDAS_REGEX.search(texto):
        return LENGUAJE_INAPROPIADO_MSG
    return None

async def enviar_mensaje_whatsapp(numero: str, mensaje: str):
    """Envía mensaje usando la API de WhatsApp definida en settings.whatsapp_api_url y settings.whatsapp_token"""
    logger.info(f"WHATSAPP OUT: {numero} -> {mensaje[:50]}...")
    url = settings.whatsapp_api_url
    token = settings.whatsapp_token
    payload = {
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Mensaje enviado correctamente a {numero}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP al enviar mensaje a WhatsApp: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error inesperado al enviar mensaje a WhatsApp: {str(e)}")

async def procesar_codigo_pedido(codigo: str, user_id: str) -> str:
    pedido = await consultar_pedido(codigo, user_id)

    if not pedido:
        return (
            "❌ *Pedido no encontrado*\n\n"
            f"Usuario: {user_id}\n"
            f"Código: {codigo}\n\n"
            "Verifica los datos e intenta nuevamente."
        )

    # Si el mock retorna un dict, convertirlo a PedidoResponse
    if isinstance(pedido, dict):
        pedido = PedidoResponse(**pedido)

    return (
        f"📦 *Estado de tu pedido* 📦\n\n"
        f"• Código: {pedido.codigo}\n"
        f"• Producto: {pedido.producto}\n"
        f"• Estado: {pedido.estado}\n"
        f"• Fecha: {pedido.fecha}\n"
        f"• Cliente: {pedido.cliente}\n"
        f"• Total: ${pedido.precio_total}\n\n"
        "¿Necesitas más ayuda? Escribe *ayuda* para opciones."
    )

def procesar_mensaje_desconocido() -> str:
    return (
        "🔍 *No reconozco tu solicitud*\n\n"
        "Envía tu *código de seguimiento* (ej: `PED-123`)\n"
        "o escribe *hola* para comenzar.\n"
        "Para ayuda, escribe *ayuda*."
    )


def procesar_saludo() -> str:
    return (
        "¡Hola! 👋 Soy tu asistente virtual.\n\n"
        "Para consultar tu pedido, envía tu *código de seguimiento*.\n"
        "Ejemplo: `PED-123`\n\n"
        "También puedes escribir *ayuda* para más información."
    )

def procesar_ayuda() -> str:
    return (
        "🤖 *Comandos disponibles:*\n\n"
        "• `hola` - Saludo inicial\n"
        "• `XXX-123` - Consultar pedido\n"
        "• `ayuda` - Mostrar esta ayuda\n\n"
        "Ejemplos de códigos:\n"
        "• `PED-123`\n"
        "• `ORD-456`\n"
        "• `FAC-789`"
    )

def obtener_mensaje_demo(case: str) -> dict:
    demo_cases = {
        "saludo": {"from": "1234567890", "text": "Hola"},
        "pedido_valido": {"from": "1234567890", "text": "PED-123"},
        "pedido_invalido": {"from": "1234567890", "text": "ABC-999"},
        "lenguaje_inapropiado": {"from": "1234567890", "text": "Eres un estupido bot"},
        "ayuda": {"from": "1234567890", "text": "ayuda"},
    }
    return demo_cases.get(case, demo_cases["saludo"])

async def procesar_mensaje_whatsapp(numero: str, texto: str) -> str:
    """Procesa mensajes de WhatsApp con lógica robusta y segura"""

    texto = sanitizar_texto(texto)
    advertencia = contiene_lenguaje_inapropiado(texto)
    if advertencia:
        return advertencia

    # Comandos de ayuda
    if re.fullmatch(r"ayuda|help|comandos", texto, re.IGNORECASE):
        return procesar_ayuda()

    # Saludos SOLO si el texto es exactamente un saludo
    if re.fullmatch(r"hola|inicio|buenas|hello", texto, re.IGNORECASE):
        return procesar_saludo()

    # Si hay texto y no es saludo ni ayuda, procesar como código de pedido
    if texto:
        return await procesar_codigo_pedido(texto, numero)

    return procesar_mensaje_desconocido()

# Eventos de aplicación
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando WhatsApp Bot API")
    yield
    # Shutdown
    logger.info("🛑 Cerrando WhatsApp Bot API")

app = FastAPI(
    title="WhatsApp Bot API",
    description="API para seguimiento de pedidos via WhatsApp con mejoras de rendimiento y seguridad",
    version="2.0.0",
    docs_url="/",
    lifespan=lifespan
)




@app.post('/webhook')
async def webhook_handler(request: Request):
    """Endpoint principal para webhooks de WhatsApp"""
    try:
        body = await request.json()
        # Validación estricta de datos
        if not body or "entry" not in body or not isinstance(body["entry"], list) or not body["entry"]:
            raise HTTPException(status_code=422, detail="Entry no puede estar vacío")
        try:
            webhook_data = WebhookRequest(**body)
        except Exception:
            raise HTTPException(status_code=422, detail="Entry no puede estar vacío")
        try:
            message = webhook_data.entry[0]['changes'][0]['value']['messages'][0]
            numero = message.get("from")
            texto_raw = message.get("text")
        except Exception:
            logger.error("No se pudo extraer el número o texto del mensaje entrante.")
            raise HTTPException(status_code=400, detail="Estructura de mensaje no válida")


        # Extraer el texto real del mensaje, sea string directo o dict con 'body'
        if isinstance(texto_raw, dict):
            texto = texto_raw.get("body", "").strip()
        elif texto_raw is not None:
            texto = str(texto_raw).strip()
        else:
            texto = ""

        if numero is None or texto is None:
            logger.error("No se pudo extraer el número o texto del mensaje entrante.")
            raise HTTPException(status_code=400, detail="Estructura de mensaje no válida")

        logger.info(f"WHATSAPP IN: {numero} -> {texto}")


        # Procesar siempre el mensaje a través de la función centralizada
        if not texto:
            raise HTTPException(status_code=422, detail="Mensaje no válido o vacío")

        respuesta = await procesar_mensaje_whatsapp(numero, texto)
        await enviar_mensaje_whatsapp(numero, respuesta)

        # Si la respuesta es la advertencia de lenguaje inapropiado, informar explícitamente
        if respuesta == LENGUAJE_INAPROPIADO_MSG:
            return {"status": "success", "message": "Lenguaje inapropiado detectado"}
        return {"status": "success", "message": "Mensaje procesado correctamente"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error en webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando el mensaje"
        )


@app.get("/api/v1/pedido/{user_id}/{codigo}", response_model=PedidoResponse)
async def obtener_pedido(user_id: str, codigo: str):
    """Endpoint para consultar pedidos directamente"""
    # Si user_id o código contienen lenguaje inapropiado, mostrar advertencia
    advertencia_user = contiene_lenguaje_inapropiado(user_id)
    advertencia_codigo = contiene_lenguaje_inapropiado(codigo)
    if advertencia_user or advertencia_codigo:
        raise HTTPException(
            status_code=400,
            detail=advertencia_user or advertencia_codigo
        )
    pedido = await consultar_pedido(codigo, user_id)
    if pedido:
        return pedido
    raise HTTPException(
        status_code=404, 
        detail=f"Pedido con código {codigo} no encontrado"
    )

@app.get("/demo")
async def demo_endpoint(case: str = "saludo"):
    """Endpoint para pruebas con casos demo"""
    return {
        "case": case,
        "url": f"/webhook?case={case}",
        "available_cases": ["saludo", "pedido_valido", "pedido_invalido", "lenguaje_inapropiado", "ayuda"]
    }

@app.get("/health")
async def health_check():
    """Endpoint de salud del sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(pedidos_cache.cache),
        "debug_mode": settings.debug_mode
    }

from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verificar_admin(credentials: HTTPBasicCredentials = Depends(security)):
    # Usuario y contraseña de admin por variables de entorno (mejor que hardcode)
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin123")
    correct_user = secrets.compare_digest(credentials.username, admin_user)
    correct_pass = secrets.compare_digest(credentials.password, admin_pass)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail="No autorizado")
    return True

@app.get("/cache/clear")
async def clear_cache(autorizado: bool = Depends(verificar_admin)):
    """Endpoint para limpiar el caché manualmente (ahora protegido)"""
    pedidos_cache.cache.clear()
    return {"status": "success", "message": "Caché limpiado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
