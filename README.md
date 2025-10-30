# Asistente IA Autónomo v2.0.0

Un asistente de programación autónomo y eficiente con memoria a largo plazo (RAG) que utiliza Gemini y Ollama de manera inteligente.

## 🚀 Características Principales

- **Arquitectura Modular**: Código organizado en clases y componentes reutilizables
- **Sistema de Memoria**: Almacena y recupera información relevante usando ChromaDB
- **Gestión Inteligente de Modelos**: Fallback automático entre Gemini y Ollama
- **Herramientas Dinámicas**: Sistema extensible de herramientas que se cargan automáticamente
- **Logging Avanzado**: Sistema de logging estructurado con Rich
- **Manejo Robusto de Errores**: Validaciones y recuperación de errores mejoradas
- **Interfaz Amigable**: Interfaz de línea de comandos mejorada con Rich

## 📋 Requisitos

### Dependencias Python
```bash
pip install chromadb rich ollama
```

### Para Gemini (opcional)
```bash
pip install google-generativeai google-api-core
```

### Ollama
```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelos
ollama pull llama2
ollama pull codellama
ollama pull mistral
ollama pull nomic-embed-text
```

## 🔧 Instalación

1. **Clonar o descargar el proyecto**
```bash
git clone <url-del-repositorio>
cd asistente-ia-autonomo
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar API keys (opcional)**
```bash
# Crear archivo keys.json
{
  "gemini_api_keys": [
    "tu-api-key-aquí"
  ]
}
```

4. **Crear directorios necesarios**
```bash
mkdir -p agent_tools desarrollos
```

## 🎯 Uso

### Ejecución básica
```bash
python main_mejorado.py
```

### Ver versión
```bash
python main_mejorado.py --version
```

### Interacción
Una vez iniciado, el asistente estará listo para recibir comandos:

```
¿Qué deseas hacer?
> Crea un script Python que calcule el factorial de un número
```

## 🔧 Herramientas Disponibles

### Herramientas Estáticas
- `write_file`: Escribe archivos
- `read_file`: Lee archivos
- `run_shell_command`: Ejecuta comandos del sistema
- `get_current_datetime`: Obtiene fecha y hora
- `finish_task`: Marca una tarea como completada
- `request_more_steps`: Solicita más pasos para una tarea
- `return_text`: Devuelve texto como resultado

### Herramientas Dinámicas
Coloca archivos Python con funciones decoradas con `@tool` en el directorio `agent_tools/` y se cargarán automáticamente.

Ejemplo de herramienta dinámica:
```python
# agent_tools/mi_herramienta.py

def tool(func):
    func._is_tool = True
    return func

@tool
def mi_herramienta(parametro: str) -> str:
    """Descripción de la herramienta"""
    return f"Resultado: {parametro}"
```

## 🧠 Sistema de Memoria

El asistente utiliza ChromaDB para almacenar y recuperar información relevante:

- **Guardado automático**: Información importante se guarda automáticamente
- **Recuperación contextual**: Busca memorias relevantes para cada tarea
- **Persistencia**: Las memorias se mantienen entre sesiones

## 🔄 Gestión de Modelos

### Orden de preferencia
1. **Gemini** (si hay API key válida)
   - Intenta usar los modelos más recientes primero
   - Fallback automático entre diferentes modelos Gemini
   - Manejo de cuotas y límites

2. **Ollama** (siempre disponible)
   - Selección interactiva de modelos
   - Funciona sin conexión a internet
   - Optimizado para tareas de programación

## 📁 Estructura del Proyecto

```
├── main_mejorado.py      # Código principal mejorado
├── config.json           # Configuración del sistema
├── README.md             # Este archivo
├── agent_memory/         # Base de datos de memoria
├── agent_tools/          # Herramientas dinámicas
├── desarrollos/          # Proyectos creados
└── keys.json            # API keys (no incluir en git)
```

## 🔍 Logging y Debugging

### Niveles de log
- **DEBUG**: Información detallada para desarrollo
- **INFO**: Información general de operación
- **WARNING**: Advertencias sobre problemas menores
- **ERROR**: Errores que requieren atención

### Archivos de log
- `agent_debug.log`: Log detallado en formato texto
- Consola: Output con formato Rich y colores

## 🛡️ Seguridad

- **Validación de entradas**: Todas las entradas se validan antes de procesar
- **Manejo seguro de archivos**: Verifica rutas y permisos
- **Control de recursos**: Límites en el número de pasos por tarea
- **Sin ejecución arbitraria**: No ejecuta código Python arbitrario

## 🚀 Mejoras Implementadas

### 1. **Arquitectura Coherente**
- Código organizado en clases especializadas
- Separación clara de responsabilidades
- Patrones de diseño aplicados

### 2. **Eficiencia Mejorada**
- Gestión inteligente de recursos
- Caché de modelos disponibles
- Logging estructurado

### 3. **Precisión Aumentada**
- Validación robusta de entradas
- Manejo mejorado de errores
- Respuestas más consistentes

### 4. **Autonomía**
- Sistema de memoria persistente
- Toma de decisiones inteligente
- Fallback automático entre modelos

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para detalles.

## 🆘 Soporte

Si encuentras problemas:

1. Verifica los logs en `agent_debug.log`
2. Asegúrate de que todas las dependencias estén instaladas
3. Comprueba que Ollama esté ejecutándose
4. Para Gemini, verifica tu API key

Para reportar bugs o solicitar features, abre un issue en el repositorio.

---

**¡Disfruta usando tu asistente IA autónomo mejorado!** 🤖✨