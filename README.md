# 🤖 WhatsApp Bot API - Seguimiento de Pedidos

API automatizada para atención al cliente via WhatsApp que permite consultar el estado de pedidos de forma inteligente.

## 🚀 Características

- **Consulta automática de pedidos** mediante códigos de seguimiento
- **Filtrado de lenguaje inapropiado** con palabras prohibidas
- **Sistema de caché inteligente** con TTL configurable
- **Reintentos automáticos** con backoff exponencial
- **Modo debug** para desarrollo y pruebas
- **Logging completo** con archivos de registro
- **Validación robusta** de datos de entrada
- **API REST** para consultas directas

## 📋 Requisitos

- Python 3.8+
- FastAPI
- WhatsApp Business API (configurada)

## 🛠️ Instalación

1. **Clonar el repositorio:**
```bash
git clone <repository-url>
cd automatizacion-atencion-cliente-whatsapp
```

2. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**
```bash
cp config.example .env
# Editar .env con tus credenciales
```

## ⚙️ Configuración

Copia `config.example` a `.env` y configura las siguientes variables:

```env
# API de pedidos
API_PEDIDOS_URL=https://mock.apidog.com/m1/1024543-1011214-default/api/v1/pedidos-whatsapp

# WhatsApp Business API
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/TU_PHONE_NUMBER_ID/messages
WHATSAPP_TOKEN=tu_token_whatsapp

# Configuración opcional
CACHE_TIMEOUT=300
MAX_RETRIES=3
REQUEST_TIMEOUT=10.0
DEBUG_MODE=false
```

## 🚀 Uso

### Ejecutar el servidor:
```bash
python main.py
```

O con uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints disponibles:

- **`/`** - Documentación interactiva (Swagger UI)
- **`/webhook`** - Webhook principal de WhatsApp
- **`/api/v1/pedido/{user_id}/{codigo}`** - Consulta directa de pedidos. Se especifica el **user_id** (número celular con el código de país correspondiente) para simular de mejor manera la consulta
- **`/health`** - Estado del sistema
- **`/cache/clear`** - Limpiar caché manualmente
- **`/demo`** - Pruebas con casos demo

## 📱 Funcionalidades del Bot

### Comandos disponibles:
- **`hola`** - Saludo inicial
- **`1`** - Consultar pedido
- **`ayuda`** - Mostrar comandos disponibles

## 🔧 Mejoras Implementadas

### Versión 2.0.0:
- ✅ **Caché con TTL** - Expiración automática de datos
- ✅ **Reintentos inteligentes** - Backoff exponencial
- ✅ **Validación robusta** - Verificación de formatos
- ✅ **Logging mejorado** - Archivos de registro
- ✅ **Manejo de errores** - Respuestas más informativas
- ✅ **Filtrado mejorado** - Más palabras prohibidas
- ✅ **Emojis por estado** - Mejor experiencia visual
- ✅ **Endpoints adicionales** - Health check, limpieza de caché
- ✅ **Documentación completa** - README y docstrings

## 🧪 Pruebas

### Ejecutar pruebas:
```bash
# Instalar dependencias de pruebas
pip install -r requirements.txt

# Ejecutar todas las pruebas
pytest

# Ejecutar con cobertura
pytest --cov=main --cov-report=html

# Ejecutar pruebas específicas
pytest tests/test_main.py -v
pytest tests/test_integration.py -v

# Ejecutar solo pruebas unitarias
pytest -m unit

# Ejecutar solo pruebas de integración
pytest -m integration
```

### Modo Debug:
```bash
# Activar modo debug en .env
DEBUG_MODE=true
```

### Casos de prueba disponibles:
- `saludo` - Mensaje de bienvenida
- `pedido_valido` - Consulta exitosa
- `pedido_invalido` - Código inexistente
- `lenguaje_inapropiado` - Filtrado de contenido
- `ayuda` - Comandos disponibles

### Probar endpoints en local:
```bash
# Health check
curl http://localhost:8000/health

# Consulta directa
curl http://localhost:8000/api/v1/pedido/+584243711009/1

# Demo
curl http://localhost:8000/demo?case=saludo
```

## 🐳 Docker

### Construir imagen:
```bash
docker build -t whatsapp-bot .
```

### Ejecutar contenedor:
```bash
docker run -p 8000:8000 --env-file .env whatsapp-bot
```

### Docker Compose:

#### Producción:
```bash
# Iniciar servicios de producción
docker-compose up -d

# Ver logs
docker-compose logs -f whatsapp-bot

# Detener servicios
docker-compose down
```

#### Desarrollo:
```bash
# Iniciar con hot-reload
docker-compose --profile dev up -d

# Ejecutar pruebas
docker-compose --profile test up --abort-on-container-exit

# Ver logs en tiempo real
docker-compose --profile logs up
```

#### Producción con Nginx:
```bash
# Iniciar con proxy reverso
docker-compose --profile production up -d

# Verificar servicios
docker-compose ps
```

#### Comandos útiles:
```bash
# Reconstruir imagen
docker-compose build --no-cache

# Reiniciar servicio
docker-compose restart whatsapp-bot

# Ver logs de todos los servicios
docker-compose logs -f

# Limpiar volúmenes
docker-compose down -v
```

#### Script de utilidades:
```bash
# Hacer ejecutable el script
chmod +x scripts/docker-utils.sh

# Desarrollo
./scripts/docker-utils.sh dev

# Producción
./scripts/docker-utils.sh prod

# Producción con Nginx
./scripts/docker-utils.sh prod-nginx

# Ejecutar pruebas
./scripts/docker-utils.sh test

# Ver logs
./scripts/docker-utils.sh logs

# Verificar salud
./scripts/docker-utils.sh health

# Limpiar todo
./scripts/docker-utils.sh clean
```

## 🔄 CI/CD

El proyecto incluye GitHub Actions para:

- **Pruebas automáticas** en múltiples versiones de Python
- **Análisis de código** con flake8, black, isort
- **Verificación de seguridad** con bandit y safety
- **Cobertura de código** con pytest-cov
- **Despliegue automático** en releases

### Workflows disponibles:
- `.github/workflows/ci.yml` - Pipeline de CI/CD
- `.github/workflows/deploy.yml` - Despliegue automático

## 📊 Monitoreo

### Logs:
- **app.log** - Registro de eventos en producción
- **Console** - Logs en tiempo real

### Métricas disponibles:
- Tamaño del caché
- Estado del sistema
- Modo de operación

## 🔒 Seguridad

- Validación de URLs
- Filtrado de contenido inapropiado
- Timeouts configurables
- Manejo seguro de errores
- Headers de seguridad

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 🆘 Soporte

Para soporte técnico o preguntas:
- Revisa la documentación en `/`
- Consulta los logs en `app.log`
- Verifica la configuración en `.env`

## Changelog

### 2025-08-05
- **Filtro de lenguaje:** Si el usuario ingresa una palabra prohibida, el bot responde SIEMPRE con un mensaje de advertencia, incluso si coincide con el formato de código.
- **Sanitización:** El texto de entrada es sanitizado antes de procesar comandos o validaciones.
- **Caché:** El caché sigue siendo en memoria, pero ahora está protegido contra acceso no autorizado.

#### Variables de entorno adicionales
- `ADMIN_USER`: Usuario admin para limpiar caché (por defecto: `admin`)
- `ADMIN_PASS`: Contraseña admin para limpiar caché (por defecto: `admin123`)

#### Respuesta ante lenguaje inapropiado
Si el usuario escribe una palabra prohibida, el bot responde:
```
⚠️ *Lenguaje inapropiado detectado*

Por favor mantén un tono respetuoso.
Estoy aquí para ayudarte con tu pedido.
```

## Demo
Se puede probar la API en el siguiente enlace:
https://automatizacion-atencion-cliente-whatsapp.onrender.com/

Desarrollado por [Neo-Gerardo]