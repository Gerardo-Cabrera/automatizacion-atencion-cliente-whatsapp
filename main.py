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
    level=logging.INFO if not settings.debug_mode else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if not settings.debug_mode else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Filtro de lenguaje mejorado
PALABRAS_PROHIBIDAS = {
    "estupido", "idiota", "imbecil", "tonto", "pendejo", "pendeja",
    "hijo de puta", "hija de puta", "puta", "cabrón", "cabrona"
}
PROHIBIDAS_REGEX = re.compile(rf"\b({'|'.join(PALABRAS_PROHIBIDAS)})\b", re.IGNORECASE)

# Modelos Pydantic mejorados
class PedidoResponse(BaseModel):
    codigo: str
    estado: str
    fecha: str
    producto: str
    cliente: str
    
    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v):
        if not re.match(r'^[A-Z]{3}-\d{3}$', v):
            raise ValueError('Código debe tener formato XXX-123')
        return v

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
async def consultar_pedido_api(codigo: str) -> Optional[PedidoResponse]:
    """Consulta la API externa de pedidos usando URL de .env"""
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        headers = {
            "X-Request-ID": str(uuid.uuid4()),
            "User-Agent": "WhatsApp-Bot/1.0.0"
        }
        response = await client.get(
            f"{settings.api_pedidos_url}/{codigo}",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        return PedidoResponse(
            codigo=data["codigo"],
            estado=data["estado"],
            fecha=data["fechaActualizacion"],
            producto=data["producto"],
            cliente=data["cliente"]
        )

async def consultar_pedido(codigo: str) -> Optional[PedidoResponse]:
    """Consulta un pedido con caché mejorado"""
    # Limpiar caché expirado periódicamente
    if len(pedidos_cache.cache) > 100:  # Limpiar cuando hay muchos elementos
        pedidos_cache.clear_expired()
    
    codigo = codigo.upper().strip().replace(" ", "")
    
    # Validar formato del código
    if not re.match(r'^[A-Z]{3}-\d{3}$', codigo):
        return None
    
    cached_pedido = pedidos_cache.get(codigo)
    if cached_pedido:
        logger.debug(f"Usando caché para pedido {codigo}")
        return cached_pedido
    
    pedido = await consultar_pedido_api(codigo)
    
    if pedido:
        pedidos_cache.set(codigo, pedido)
    
    return pedido

def contiene_lenguaje_inapropiado(texto: str) -> bool:
    """Verifica si el texto contiene lenguaje inapropiado"""
    return bool(PROHIBIDAS_REGEX.search(texto))

async def enviar_mensaje_whatsapp(numero: str, mensaje: str):
    """Envía mensaje usando URL y token de .env con mejor manejo de errores"""
    logger.info(f"WHATSAPP OUT: {numero} -> {mensaje[:50]}...")
    
    if settings.debug_mode:
        logger.debug(f"[DEBUG MODE] Mensaje simulado enviado a {numero}")
        return
    
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            headers = {
                "Authorization": f"Bearer {settings.whatsapp_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": numero,
                "text": {"body": mensaje}
            }
            response = await client.post(
                settings.whatsapp_api_url, 
                json=payload, 
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"Mensaje enviado exitosamente a {numero}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a {numero}: {str(e)}")
        raise

def procesar_saludo() -> str:
    return (
        "¡Hola! 👋 Soy tu asistente virtual.\n\n"
        "Para consultar tu pedido, envía tu *código de seguimiento*.\n"
        "Ejemplo: `PED-123`\n\n"
        "También puedes escribir *ayuda* para más información."
    )

async def procesar_codigo_pedido(codigo: str) -> str:
    pedido = await consultar_pedido(codigo)
    
    if not pedido:
        return (
            "❌ *Pedido no encontrado*\n\n"
            "Verifica el código e inténtalo nuevamente.\n"
            "Formato correcto: `XXX-123`\n"
            "Ejemplo: `PED-123`"
        )
    
    # Emojis según estado
    estado_emoji = {
        "pendiente": "⏳",
        "en_proceso": "🔄", 
        "enviado": "📦",
        "entregado": "✅",
        "cancelado": "❌"
    }
    
    emoji = estado_emoji.get(pedido.estado.lower(), "📋")
    
    return (
        f"📦 *Estado de tu pedido* 📦\n\n"
        f"• Código: `{pedido.codigo}`\n"
        f"• Producto: {pedido.producto}\n"
        f"• Estado: {emoji} {pedido.estado}\n"
        f"• Actualización: {pedido.fecha}\n"
        f"• Cliente: {pedido.cliente}\n\n"
        "¿Necesitas más ayuda? Escribe *ayuda* para opciones."
    )

def procesar_mensaje_desconocido() -> str:
    return (
        "🔍 *No reconozco tu solicitud*\n\n"
        "Envía tu *código de seguimiento* (ej: `PED-123`)\n"
        "o escribe *hola* para comenzar.\n"
        "Para ayuda, escribe *ayuda*."
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
    """Procesa mensajes de WhatsApp con mejor lógica"""
    texto = texto.strip()
    
    # Verificar lenguaje inapropiado
    if contiene_lenguaje_inapropiado(texto):
        return (
            "⚠️ *Lenguaje inapropiado detectado*\n\n"
            "Por favor mantén un tono respetuoso.\n"
            "Estoy aquí para ayudarte con tu pedido."
        )

    # Comandos de ayuda
    if re.search(r"ayuda|help|comandos", texto, re.IGNORECASE):
        return procesar_ayuda()
    
    # Saludos
    if re.search(r"hola|inicio|buenas|hello", texto, re.IGNORECASE):
        return procesar_saludo()
    
    # Códigos de pedido
    if match := re.match(r"^[a-zA-Z]{3}[-]?\d{3}$", texto):
        return await procesar_codigo_pedido(match.group())
    
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
        query_params = request.query_params
        case = query_params.get("case", "saludo")
        
        if settings.debug_mode and case:
            message = obtener_mensaje_demo(case)
        else:
            # Validar estructura del webhook
            webhook_data = WebhookRequest(**body)
            message = webhook_data.entry[0]['changes'][0]['value']['messages'][0]
        
        numero = message["from"]
        texto = message["text"].strip()
        logger.info(f"WHATSAPP IN: {numero} -> {texto}")

        respuesta = await procesar_mensaje_whatsapp(numero, texto)
        await enviar_mensaje_whatsapp(numero, respuesta)
        
        return {"status": "success", "message": "Mensaje procesado correctamente"}

    except Exception as e:
        logger.exception(f"Error en webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando el mensaje"
        )

@app.get("/api/v1/pedido/{codigo}", response_model=PedidoResponse)
async def obtener_pedido(codigo: str):
    """Endpoint para consultar pedidos directamente"""
    pedido = await consultar_pedido(codigo)
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

@app.get("/cache/clear")
async def clear_cache():
    """Endpoint para limpiar el caché manualmente"""
    pedidos_cache.cache.clear()
    return {"status": "success", "message": "Caché limpiado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
