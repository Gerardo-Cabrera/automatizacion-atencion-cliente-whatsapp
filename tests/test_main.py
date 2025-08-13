import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app, procesar_saludo, procesar_ayuda, contiene_lenguaje_inapropiado
from main import procesar_mensaje_desconocido, CacheManager, PedidoResponse
client = TestClient(app)
class TestWhatsAppBot:
    """Pruebas para el bot de WhatsApp"""
    
    def test_procesar_saludo(self):
        """Prueba el mensaje de saludo"""
        respuesta = procesar_saludo()
        assert "Hola" in respuesta
        assert "asistente virtual" in respuesta
        assert "código de seguimiento" in respuesta
    
    def test_procesar_ayuda(self):
        """Prueba el mensaje de ayuda"""
        respuesta = procesar_ayuda()
        assert "Comandos disponibles" in respuesta
        assert "hola" in respuesta
        assert "XXX-123" in respuesta
    
    def test_procesar_mensaje_desconocido(self):
        """Prueba el mensaje para solicitudes desconocidas"""
        respuesta = procesar_mensaje_desconocido()
        assert "No reconozco" in respuesta
        assert "código de seguimiento" in respuesta
    
    def test_contiene_lenguaje_inapropiado(self):
        """Prueba el filtro de lenguaje inapropiado"""
        # Casos positivos
        assert contiene_lenguaje_inapropiado("Eres un estupido bot")
        assert contiene_lenguaje_inapropiado("No seas IDIOTA")
        assert contiene_lenguaje_inapropiado("Eres un pendejo")
        
        # Casos negativos
        assert not contiene_lenguaje_inapropiado("Hola, ¿cómo estás?")
        assert not contiene_lenguaje_inapropiado("Quiero consultar mi pedido")
        assert not contiene_lenguaje_inapropiado("")
class TestCacheManager:
    """Pruebas para el gestor de caché"""
    
    def test_cache_set_get(self):
        """Prueba almacenar y recuperar del caché"""
        cache = CacheManager(ttl_seconds=300)
        cache.set("test_key", "test_value")
        
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_cache_expiration(self):
        """Prueba la expiración del caché"""
        cache = CacheManager(ttl_seconds=1)
        cache.set("test_key", "test_value")
        
        # Esperar a que expire
        import time
        time.sleep(1.1)
        
        result = cache.get("test_key")
        assert result is None
    
    def test_clear_expired(self):
        """Prueba la limpieza de elementos expirados"""
        cache = CacheManager(ttl_seconds=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Esperar a que expire
        import time
        time.sleep(1.1)
        
        cache.clear_expired()
        assert len(cache.cache) == 0
class TestPedidoResponse:
    """Pruebas para el modelo de respuesta de pedido"""
    
    def test_valid_codigo(self):
        """Prueba código válido"""
        pedido = PedidoResponse(
            estado="pendiente",
            fecha="2024-01-01",
            producto="Producto Test",
            precio_total="100 USD"
        )
    # El campo 'codigo' ya no existe en el modelo PedidoResponse
class TestAPIEndpoints:
    """Pruebas para los endpoints de la API"""
    
    def test_health_endpoint(self):
        """Prueba el endpoint de salud"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "cache_size" in data
    
    def test_demo_endpoint(self):
        """Prueba el endpoint de demo"""
        response = client.get("/demo")
        assert response.status_code == 200
        data = response.json()
        assert "case" in data
        assert "url" in data
        assert "available_cases" in data
    
    def test_cache_clear_endpoint(self):
        """Prueba el endpoint de limpieza de caché"""
        import base64
        # Autenticación básica por defecto: admin/admin123
        credentials = base64.b64encode(b"admin:admin123").decode("utf-8")
        headers = {"Authorization": f"Basic {credentials}"}
        response = client.get("/cache/clear", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Caché limpiado" in data["message"]
    
    def test_pedido_endpoint_not_found(self):
        """Prueba el endpoint de pedido con código inexistente"""
        response = client.get("/api/v1/pedido/INV-999/INV-999")
        assert response.status_code == 404
        data = response.json()
        assert "no encontrado" in data["detail"].lower()
@pytest.mark.asyncio
class TestAsyncFunctions:
    """Pruebas para funciones asíncronas"""
    
    @patch('main.consultar_pedido_api')
    async def test_consultar_pedido_success(self, mock_api):
        """Prueba consulta exitosa de pedido"""
        from main import consultar_pedido
        # Mock de respuesta exitosa
        mock_pedido = PedidoResponse(
            estado="pendiente",
            fecha="2024-01-01",
            producto="Producto Test",
            precio_total="100 USD"
        )
        mock_api.return_value = mock_pedido
        result = await consultar_pedido("PED-123", "1")
        assert result is not None
    # El campo 'codigo' ya no existe en el modelo PedidoResponse
    @patch('main.consultar_pedido_api')
    async def test_consultar_pedido_not_found(self, mock_api):
        """Prueba consulta de pedido inexistente"""
        from main import consultar_pedido
        mock_api.return_value = None
        result = await consultar_pedido("PED-999", "1")
        assert result is None
    
    @patch('main.enviar_mensaje_whatsapp')
    async def test_procesar_mensaje_whatsapp_saludo(self, mock_send):
        """Prueba procesamiento de mensaje de saludo"""
        from main import procesar_mensaje_whatsapp
        
        result = await procesar_mensaje_whatsapp("1234567890", "hola")
        assert "Hola" in result
        assert "asistente virtual" in result
    
    @patch('main.enviar_mensaje_whatsapp')
    async def test_procesar_mensaje_whatsapp_ayuda(self, mock_send):
        """Prueba procesamiento de mensaje de ayuda"""
        from main import procesar_mensaje_whatsapp
        
        result = await procesar_mensaje_whatsapp("1234567890", "ayuda")
        assert "Comandos disponibles" in result
    
    @patch('main.enviar_mensaje_whatsapp')
    async def test_procesar_mensaje_whatsapp_lenguaje_inapropiado(self, mock_send):
        """Prueba procesamiento de mensaje con lenguaje inapropiado"""
        from main import procesar_mensaje_whatsapp
        
        result = await procesar_mensaje_whatsapp("1234567890", "Eres un estupido bot")
        assert "Lenguaje inapropiado" in result
        assert "respetuoso" in result
if __name__ == "__main__":
    pytest.main([__file__]) 