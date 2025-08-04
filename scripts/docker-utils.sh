#!/bin/bash

# Script de utilidades para Docker Compose
# Uso: ./scripts/docker-utils.sh [comando]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Función para verificar si Docker está ejecutándose
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker no está ejecutándose. Por favor inicia Docker."
        exit 1
    fi
}

# Función para verificar si Docker Compose está disponible
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose no está instalado."
        exit 1
    fi
}

# Función para desarrollo
dev() {
    print_header "Iniciando entorno de desarrollo"
    check_docker
    check_docker_compose
    
    print_message "Iniciando servicios de desarrollo..."
    docker-compose --profile dev up -d
    
    print_message "Servicios iniciados:"
    echo "  - API: http://localhost:8001"
    echo "  - Documentación: http://localhost:8001/"
    echo "  - Health check: http://localhost:8001/health"
    
    print_message "Para ver logs: docker-compose --profile dev logs -f"
}

# Función para producción
prod() {
    print_header "Iniciando entorno de producción"
    check_docker
    check_docker_compose
    
    print_message "Iniciando servicios de producción..."
    docker-compose up -d
    
    print_message "Servicios iniciados:"
    echo "  - API: http://localhost:8000"
    echo "  - Documentación: http://localhost:8000/"
    echo "  - Health check: http://localhost:8000/health"
    
    print_message "Para ver logs: docker-compose logs -f"
}

# Función para producción con Nginx
prod_nginx() {
    print_header "Iniciando entorno de producción con Nginx"
    check_docker
    check_docker_compose
    
    print_message "Iniciando servicios de producción con proxy reverso..."
    docker-compose --profile production up -d
    
    print_message "Servicios iniciados:"
    echo "  - API: http://localhost"
    echo "  - Documentación: http://localhost/"
    echo "  - Health check: http://localhost/health"
    
    print_message "Para ver logs: docker-compose logs -f"
}

# Función para pruebas
test() {
    print_header "Ejecutando pruebas"
    check_docker
    check_docker_compose
    
    print_message "Ejecutando pruebas en contenedor..."
    docker-compose --profile test up --abort-on-container-exit
    
    print_message "Pruebas completadas"
}

# Función para logs
logs() {
    print_header "Mostrando logs"
    check_docker
    check_docker_compose
    
    print_message "Iniciando visualizador de logs..."
    docker-compose --profile logs up
}

# Función para limpiar
clean() {
    print_header "Limpiando contenedores y volúmenes"
    check_docker
    check_docker_compose
    
    print_warning "Esto eliminará todos los contenedores, volúmenes y redes."
    read -p "¿Estás seguro? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_message "Deteniendo y eliminando contenedores..."
        docker-compose down -v --remove-orphans
        
        print_message "Limpiando imágenes no utilizadas..."
        docker image prune -f
        
        print_message "Limpieza completada"
    else
        print_message "Limpieza cancelada"
    fi
}

# Función para reconstruir
rebuild() {
    print_header "Reconstruyendo imágenes"
    check_docker
    check_docker_compose
    
    print_message "Reconstruyendo imágenes..."
    docker-compose build --no-cache
    
    print_message "Reconstrucción completada"
}

# Función para health check
health() {
    print_header "Verificando salud de los servicios"
    check_docker
    check_docker_compose
    
    print_message "Verificando estado de los contenedores..."
    docker-compose ps
    
    print_message "Verificando health checks..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_message "✅ API está funcionando correctamente"
    else
        print_error "❌ API no está respondiendo"
    fi
}

# Función para mostrar ayuda
help() {
    print_header "Utilidades de Docker Compose"
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  dev         - Iniciar entorno de desarrollo (puerto 8001)"
    echo "  prod        - Iniciar entorno de producción (puerto 8000)"
    echo "  prod-nginx  - Iniciar producción con Nginx (puerto 80)"
    echo "  test        - Ejecutar pruebas"
    echo "  logs        - Ver logs en tiempo real"
    echo "  clean       - Limpiar contenedores y volúmenes"
    echo "  rebuild     - Reconstruir imágenes"
    echo "  health      - Verificar salud de los servicios"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 dev"
    echo "  $0 prod"
    echo "  $0 test"
}

# Función principal
main() {
    case "${1:-help}" in
        dev)
            dev
            ;;
        prod)
            prod
            ;;
        prod-nginx)
            prod_nginx
            ;;
        test)
            test
            ;;
        logs)
            logs
            ;;
        clean)
            clean
            ;;
        rebuild)
            rebuild
            ;;
        health)
            health
            ;;
        help|--help|-h)
            help
            ;;
        *)
            print_error "Comando desconocido: $1"
            help
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@" 