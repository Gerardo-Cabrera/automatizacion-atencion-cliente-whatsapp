import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app

client = TestClient(app)

class TestIntegration:
    """Pruebas de integración para el sistema completo"""
    
    @patch('main.enviar_mensaje_whatsapp')
    @patch('main.consultar_pedido_api')
    def test_webhook_complete_flow_success(self, mock_api, mock_send):
        """Prueba el flujo completo del webhook con éxito"""
        # Mock de la API de pedidos
        mock_pedido = {
            "estado": "pendiente",
            "fecha": "2024-01-01",
            "producto": "Producto Test",
            "precio_total": "100 USD"
        }
        mock_api.return_value = mock_pedido
        # Mock del envío de WhatsApp
        mock_send.return_value = None
        # Datos del webhook
        webhook_data = {
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
        # Ejecutar webhook
        response = client.post("/webhook", json=webhook_data)
        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Verificar que se llamó la API con ambos argumentos
        mock_api.assert_called_once_with("PED-123", "1234567890")
        # Verificar que se envió el mensaje
        mock_send.assert_called_once()
    
    @patch('main.enviar_mensaje_whatsapp')
    def test_webhook_saludo(self, mock_send):
        """Prueba el webhook con mensaje de saludo"""
        # Mock del envío de WhatsApp
        mock_send.return_value = None
        
        # Datos del webhook
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "text": {
                                "body": "hola"
                            }
                        }]
                    }
                }]
            }]
        }
        
        # Ejecutar webhook
        response = client.post("/webhook", json=webhook_data)
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Verificar que se envió el mensaje
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert "Hola" in args[1]  # El mensaje contiene "Hola"
    
    @patch('main.enviar_mensaje_whatsapp')
    def test_webhook_lenguaje_inapropiado(self, mock_send):
        """Prueba el webhook con lenguaje inapropiado"""
        mock_send.return_value = None
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "text": {
                                "body": "Eres un estupido bot"
                            }
                        }]
                    }
                }]
            }]
        }
        response = client.post("/webhook", json=webhook_data)
        assert response.status_code == 200
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert "Lenguaje inapropiado" in args[1]
    
    def test_webhook_invalid_data(self):
        """Prueba el webhook con datos inválidos"""
        invalid_data = {"entry": []}
        response = client.post("/webhook", json=invalid_data)
        # El endpoint retorna 422 si entry está vacío
        assert response.status_code == 422
    
    @patch('main.consultar_pedido_api')
    def test_api_pedido_direct_endpoint(self, mock_api):
        """Prueba el endpoint directo de consulta de pedidos"""
        mock_pedido = {
            "estado": "pendiente",
            "fecha": "2024-01-01",
            "producto": "Producto Test",
            "precio_total": "100 USD"
        }
        mock_api.return_value = mock_pedido
        response = client.get("/api/v1/pedido/1/PED-123")
        assert response.status_code == 200
        data = response.json()
        assert data["codigo"] == "PED-123"
        assert data["estado"] == "pendiente"
    
    @patch('main.consultar_pedido_api')
    def test_api_pedido_not_found(self, mock_api):
        """Prueba el endpoint de pedido con código inexistente"""
        mock_api.return_value = None
        response = client.get("/api/v1/pedido/1/PED-999")
        assert response.status_code == 404
        data = response.json()
        assert "no encontrado" in data["detail"].lower()
    
    def test_demo_endpoints(self):
        """Prueba los endpoints de demo"""
        # Probar diferentes casos
        cases = ["saludo", "pedido_valido", "pedido_invalido", "lenguaje_inapropiado", "ayuda"]
        
        for case in cases:
            response = client.get(f"/demo?case={case}")
            assert response.status_code == 200
            data = response.json()
            assert data["case"] == case
            assert "url" in data
    
    def test_health_endpoint_integration(self):
        """Prueba el endpoint de salud en integración"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "status" in data
        assert "timestamp" in data
        assert "cache_size" in data
        assert "debug_mode" in data
        
        # Verificar valores
        assert data["status"] == "healthy"
        assert isinstance(data["cache_size"], int)
        assert isinstance(data["debug_mode"], bool)
    
    def test_cache_clear_integration(self):
        """Prueba la limpieza de caché en integración"""
        import base64
        credentials = base64.b64encode(b"admin:admin123").decode("utf-8")
        headers = {"Authorization": f"Basic {credentials}"}
        response1 = client.get("/cache/clear", headers=headers)
        assert response1.status_code == 200
        response2 = client.get("/cache/clear", headers=headers)
        assert response2.status_code == 200
        data1 = response1.json()
        data2 = response2.json()
        assert data1["status"] == "success"
        assert data2["status"] == "success"

if __name__ == "__main__":
    pytest.main([__file__]) 