import pytest
import asyncio
from unittest.mock import patch
import os

# Configuración para pruebas
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Configurar entorno de pruebas"""
    # Variables de entorno para pruebas
    os.environ["API_PEDIDOS_URL"] = "https://api.test.com/pedidos"
    os.environ["WHATSAPP_API_URL"] = "https://graph.facebook.com/v18.0/test/messages"
    os.environ["WHATSAPP_TOKEN"] = "test_token"
    os.environ["DEBUG_MODE"] = "true"
    os.environ["CACHE_TIMEOUT"] = "300"
    os.environ["MAX_RETRIES"] = "3"
    os.environ["REQUEST_TIMEOUT"] = "10.0"
    
    yield
    
    # Limpiar variables después de las pruebas
    for key in ["API_PEDIDOS_URL", "WHATSAPP_API_URL", "WHATSAPP_TOKEN", 
                "DEBUG_MODE", "CACHE_TIMEOUT", "MAX_RETRIES", "REQUEST_TIMEOUT"]:
        if key in os.environ:
            del os.environ[key]

@pytest.fixture
def event_loop():
    """Crear event loop para pruebas asíncronas"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_httpx_client():
    """Mock del cliente HTTP para pruebas"""
    with patch('httpx.AsyncClient') as mock_client:
        yield mock_client

@pytest.fixture
def sample_pedido_data():
    """Datos de ejemplo para un pedido"""
    return {
        "codigo": "PED-123",
        "estado": "pendiente",
        "fechaActualizacion": "2024-01-01T10:00:00Z",
        "producto": "Producto de Prueba",
        "cliente": "Cliente de Prueba"
    }

@pytest.fixture
def sample_webhook_data():
    """Datos de ejemplo para webhook de WhatsApp"""
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "text": {
                            "body": "PED-123"
                        }
                    }]
                }
            }]
        }]
    } 