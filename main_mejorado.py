#!/usr/bin/env python3
"""
Asistente IA Autónomo y Eficiente
=====================================

Un asistente de programación autónomo con memoria a largo plazo (RAG) 
que utiliza Gemini y Ollama de manera inteligente y eficiente.

Características principales:
- Arquitectura modular y coherente
- Gestión inteligente de recursos
- Sistema de memoria persistente
- Fallback automático entre modelos
- Herramientas dinámicas y extensibles
"""

# Standard library imports
import os
import sys
import json
import re
import subprocess
import uuid
import importlib.util
import inspect
import datetime
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

# Third-party imports
import chromadb
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.logging import RichHandler
import ollama

try:
    import google.generativeai as genai
    import google.generativeai.types as genai_types
    from google.generativeai.protos import ToolConfig, FunctionCallingConfig, FunctionDeclaration, Schema, Type
    from google.api_core import exceptions
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    console.print("[yellow]Advertencia: Google AI no está disponible. Solo se usará Ollama.[/yellow]")

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

@dataclass
class Config:
    """Configuración central del asistente"""
    # Sistema
    APP_NAME: str = "Asistente IA Autónomo"
    VERSION: str = "2.0.0"
    
    # Archivos y directorios
    LOG_FILE: str = "agent_debug.log"
    MEMORY_DIR: str = "agent_memory"
    TOOLS_DIR: str = "agent_tools"
    DEVELOPMENTS_DIR: str = "desarrollos"
    API_KEYS_FILE: str = "keys.json"
    
    # Modelos
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    MAX_STEPS_PER_TASK: int = 10
    STEP_INCREMENT: int = 10
    
    # Modelos Gemini preferidos
    PREFERRED_GEMINI_MODELS: List[str] = field(default_factory=lambda: [
        "models/gemini-2.5-flash-preview-09-2025",
        "models/gemini-2.5-flash-lite-preview-09-2025",
        "models/gemini-2.5-flash-lite",
        "models/gemini-pro",
        "models/gemini-1.5-pro",
        "models/gemini-1.5-flash"
    ])

# Instancia global de configuración
CONFIG = Config()

class ModelProvider(Enum):
    """Proveedores de modelos disponibles"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    UNKNOWN = "unknown"

@dataclass
class TaskContext:
    """Contexto de una tarea en curso"""
    task_id: Optional[str] = None
    turn_history: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def reset(self):
        """Reinicia el contexto de la tarea"""
        self.task_id = None
        self.turn_history.clear()
        self.start_time = datetime.datetime.now()

# ============================================================================
# SISTEMA DE LOGGING MEJORADO
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configura el sistema de logging con Rich"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=Console(), rich_tracebacks=True)]
    )
    
    # Logger específico para el agente
    agent_logger = logging.getLogger("agent")
    agent_logger.setLevel(logging.DEBUG)
    
    # Handler para archivo
    file_handler = logging.FileHandler(CONFIG.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    agent_logger.addHandler(file_handler)
    
    return agent_logger

# Configurar logging global
logger = setup_logging()
console = Console()

# ============================================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================================

class GeminiQuotaExceededError(Exception):
    """Excepción cuando la cuota de Gemini ha sido excedida"""
    pass

class ModelNotAvailableError(Exception):
    """Excepción cuando ningún modelo está disponible"""
    pass

class ToolExecutionError(Exception):
    """Excepción en la ejecución de herramientas"""
    pass

# ============================================================================
# GESTOR DE MODELOS
# ============================================================================

class ModelManager:
    """Gestor centralizado de modelos de IA"""
    
    def __init__(self, tool_manager: Optional['ToolManager'] = None):
        self.current_provider: ModelProvider = ModelProvider.UNKNOWN
        self.gemini_model: Optional[str] = None
        self.ollama_model: Optional[str] = None
        self.api_keys: List[str] = []
        self._available_models_cache: Dict[str, List[str]] = {}
        self.tool_manager = tool_manager
    
    def initialize(self) -> bool:
        """Inicializa los modelos disponibles"""
        try:
            # Intentar configurar Gemini
            if self._setup_gemini():
                self.current_provider = ModelProvider.GEMINI
                logger.info("Gemini configurado como proveedor principal")
                return True
            
            # Si Gemini falla, intentar Ollama
            if self._setup_ollama():
                self.current_provider = ModelProvider.OLLAMA
                logger.info("Ollama configurado como proveedor principal")
                return True
                
            raise ModelNotAvailableError("Ningún modelo está disponible")
            
        except Exception as e:
            logger.error(f"Error inicializando modelos: {e}")
            return False
    
    def _setup_gemini(self) -> bool:
        """Configura Gemini si está disponible"""
        if not GOOGLE_AI_AVAILABLE:
            logger.debug("Google AI no está disponible")
            return False
            
        try:
            # Cargar API keys
            self.api_keys = self._load_api_keys()
            if not self.api_keys or "TU_API_KEY" in self.api_keys[0]:
                logger.warning("No se encontraron API keys válidas de Gemini")
                return False
            
            # Probar conexión
            genai.configure(api_key=self.api_keys[0])
            available_models = [m.name for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
            
            # Seleccionar mejor modelo
            for preferred in CONFIG.PREFERRED_GEMINI_MODELS:
                if preferred in available_models:
                    self.gemini_model = preferred
                    break
            
            if not self.gemini_model and available_models:
                self.gemini_model = available_models[0]
            
            logger.info(f"Modelo Gemini seleccionado: {self.gemini_model}")
            return self.gemini_model is not None
            
        except Exception as e:
            logger.error(f"Error configurando Gemini: {e}")
            return False
    
    def _setup_ollama(self) -> bool:
        """Configura Ollama"""
        try:
            local_models = ollama.list()['models']
            if not local_models:
                logger.error("No se encontraron modelos en Ollama")
                return False
            
            # Seleccionar modelo
            if len(local_models) == 1:
                self.ollama_model = local_models[0]['model']
            else:
                self.ollama_model = self._select_ollama_model_interactive(local_models)
            
            logger.info(f"Modelo Ollama seleccionado: {self.ollama_model}")
            return self.ollama_model is not None
            
        except Exception as e:
            logger.error(f"Error configurando Ollama: {e}")
            return False
    
    def _load_api_keys(self) -> List[str]:
        """Carga las API keys desde archivo"""
        try:
            script_dir = Path(__file__).parent
            keys_file = script_dir / CONFIG.API_KEYS_FILE
            
            if keys_file.exists():
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
                    return keys_data.get("gemini_api_keys", [])
            
            return []
        except Exception as e:
            logger.error(f"Error cargando API keys: {e}")
            return []
    
    def _select_ollama_model_interactive(self, models: List[Dict]) -> str:
        """Selecciona un modelo Ollama de forma interactiva"""
        console.print("\n[bold cyan]Modelos de Ollama disponibles:[/bold cyan]")
        for i, model in enumerate(models, 1):
            console.print(f"  {i}. {model['model']}")
        
        while True:
            try:
                choice = Prompt.ask("\nSelecciona un modelo", default="1")
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    return models[idx]['model']
                console.print("[red]Selección inválida[/red]")
            except ValueError:
                console.print("[red]Entrada inválida[/red]")
    
    def get_query_function(self) -> Callable:
        """Obtiene la función de consulta según el proveedor actual"""
        if self.current_provider == ModelProvider.GEMINI:
            return self._query_gemini
        elif self.current_provider == ModelProvider.OLLAMA:
            return self._query_ollama
        else:
            raise ModelNotAvailableError("No hay proveedor configurado")
    
    def _query_gemini(self, history: List[Dict], model_name: str, api_keys: List[str], turn: int):
        """Consulta al modelo Gemini"""
        current_key = self.api_keys[turn % len(self.api_keys)]
        genai.configure(api_key=current_key)
        
        model = genai.GenerativeModel(
            model_name, 
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'block_none', 
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'block_none'
            }
        )
        
        try:
            response = model.generate_content(
                history,
                tools=self._get_gemini_tools(),
                tool_config=ToolConfig(function_calling_config=FunctionCallingConfig(mode="ANY"))
            )
            return response
            
        except exceptions.ResourceExhausted as e:
            raise GeminiQuotaExceededError("Cuota de Gemini excedida") from e
        except Exception as e:
            logger.error(f"Error consultando Gemini: {e}")
            raise
    
    def _query_ollama(self, history: List[Dict], model_name: str, api_keys: List[str], turn: int):
        """Consulta al modelo Ollama"""
        messages = []
        for item in history:
            role = 'assistant' if item['role'] == 'model' else 'user'
            content = "\n".join(item['parts'])
            messages.append({'role': role, 'content': content})
        
        # Forzar salida JSON
        response = ollama.chat(model=model_name, messages=messages, format='json')
        
        # Adaptar respuesta al formato esperado
        class OllamaResponse:
            def __init__(self, json_content):
                self.text = json_content
                self.candidates = []
        
        return OllamaResponse(response['message']['content'])
    
    def _get_gemini_tools(self):
        """Obtiene las herramientas para Gemini"""
        gemini_tools = []
        if self.tool_manager:
            for tool_name, tool_func in self.tool_manager.tools.items():
                if hasattr(tool_func, '_is_tool') and tool_func._is_tool:
                    metadata = tool_func._tool_metadata
                    gemini_tools.append(
                        FunctionDeclaration(
                            name=metadata['name'],
                            description=metadata['description'],
                            parameters=metadata['parameters']
                        )
                    )
        return gemini_tools

# ============================================================================
# SISTEMA DE MEMORIA (RAG)
# ============================================================================

class MemoryManager:
    """Gestor de memoria a largo plazo usando ChromaDB"""
    
    def __init__(self):
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection: Optional[chromadb.Collection] = None
        self.model_manager: Optional[ModelManager] = None
    
    def initialize(self, model_manager: ModelManager) -> bool:
        """Inicializa el sistema de memoria"""
        try:
            self.model_manager = model_manager
            
            # Crear directorio de memoria
            memory_path = Path(__file__).parent / CONFIG.MEMORY_DIR
            memory_path.mkdir(exist_ok=True)
            
            # Inicializar cliente ChromaDB
            self.client = chromadb.PersistentClient(path=str(memory_path))
            self.collection = self.client.get_or_create_collection(
                name="long_term_memory"
            )
            
            logger.info("Sistema de memoria inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando sistema de memoria: {e}")
            return False
    
    def save_memory(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Guarda un recuerdo en la memoria a largo plazo"""
        try:
            if not self.collection:
                return "Error: Sistema de memoria no inicializado"
            
            # Generar embedding
            embedding = self._generate_embedding(text)
            memory_id = str(uuid.uuid4())
            
            # Guardar en ChromaDB
            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
                ids=[memory_id]
            )
            
            logger.debug(f"Recuerdo guardado: {text[:50]}...")
            return "Éxito: Recuerdo guardado"
            
        except Exception as e:
            logger.error(f"Error guardando recuerdo: {e}")
            return f"Error guardando recuerdo: {e}"
    
    def retrieve_memories(self, prompt: str, n_results: int = 3) -> str:
        """Recupera recuerdos relevantes basados en un prompt"""
        try:
            if not self.collection or self.collection.count() == 0:
                return "No hay recuerdos guardados"
            
            # Generar embedding del prompt
            prompt_embedding = self._generate_embedding(prompt)
            
            # Buscar recuerdos similares
            results = self.collection.query(
                query_embeddings=[prompt_embedding],
                n_results=n_results
            )
            
            # Formatear resultados
            memories = "\n".join([f"- {doc}" for doc in results['documents'][0]])
            return memories
            
        except Exception as e:
            logger.error(f"Error recuperando recuerdos: {e}")
            return f"Error recuperando recuerdos: {e}"
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Genera un embedding para el texto dado"""
        try:
            # Usar Ollama para embeddings por defecto
            response = ollama.embeddings(
                model=CONFIG.OLLAMA_EMBEDDING_MODEL, 
                prompt=text
            )
            return response['embedding']
            
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            # Fallback a vector de ceros
            return [0.0] * 768

from agent_tools.tool_decorator import tool



# ============================================================================

# GESTOR DE HERRAMIENTAS

# ============================================================================



class ToolManager:
    """Gestor de herramientas dinámicas y estáticas"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.static_tools_initialized = False
    
    def initialize(self) -> bool:
        """Inicializa el gestor de herramientas"""
        try:
            # Cargar herramientas estáticas
            self._initialize_static_tools()
            
            # Cargar herramientas dinámicas
            self._load_dynamic_tools()
            
            logger.info(f"Herramientas cargadas: {list(self.tools.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando herramientas: {e}")
            return False
    
    def _initialize_static_tools(self):
        """Inicializa las herramientas estáticas del sistema"""
        @tool
        def write_file(file_path: str, content: str) -> str:
            """Escribe o reescribe un archivo"""
            try:
                full_path = Path(__file__).parent / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Archivo escrito: {file_path}")
                return f"Éxito: Archivo '{file_path}' guardado"
                
            except Exception as e:
                return f"Error escribiendo archivo: {e}"
        
        @tool
        def read_file(file_path: str) -> str:
            """Lee el contenido de un archivo"""
            try:
                full_path = Path(__file__).parent / file_path
                
                if not full_path.exists():
                    return f"Error: El archivo '{file_path}' no existe"
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return f"Contenido de '{file_path}':\n{content}"
                
            except Exception as e:
                return f"Error leyendo archivo: {e}"
        
        @tool
        def run_shell_command(command: str) -> str:
            """Ejecuta un comando de shell"""
            try:
                logger.info(f"Ejecutando comando: {command}")
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=Path(__file__).parent
                )
                
                output = f"STDOUT:\n{result.stdout}"
                if result.stderr:
                    output += f"\nSTDERR:\n{result.stderr}"
                
                return output
                
            except Exception as e:
                return f"Error ejecutando comando: {e}"
        
        @tool
        def get_current_datetime() -> str:
            """Obtiene la fecha y hora actuales"""
            return datetime.datetime.now().isoformat()
        
        @tool
        def finish_task(message: str = "Tarea completada") -> str:
            """Señala que la tarea actual ha sido completada"""
            return f"Tarea finalizada: {message}"
        
        @tool
        def request_more_steps(reason: str = "Necesito más pasos") -> str:
            """Solicita más pasos para completar la tarea"""
            return f"Solicitando más pasos: {reason}"
        
        @tool
        def return_text(text: str) -> str:
            """Devuelve el texto de entrada como resultado"""
            return text
        
        # Registrar herramientas estáticas
        self.tools.update({
            'write_file': write_file,
            'read_file': read_file,
            'run_shell_command': run_shell_command,
            'get_current_datetime': get_current_datetime,
            'finish_task': finish_task,
            'request_more_steps': request_more_steps,
            'return_text': return_text
        })
        
        self.static_tools_initialized = True
    
    def _load_dynamic_tools(self):
        """Carga herramientas dinámicas desde el directorio agent_tools"""
        try:
            tools_dir = Path(__file__).parent / CONFIG.TOOLS_DIR
            
            if not tools_dir.exists():
                logger.debug(f"Directorio de herramientas no existe: {tools_dir}")
                return
            
            # Añadir directorio al path de Python
            sys.path.insert(0, str(tools_dir.parent))
            
            for file_path in tools_dir.glob("*.py"):
                if file_path.name == "__init__.py":
                    continue
                
                try:
                    # Cargar módulo
                    spec = importlib.util.spec_from_file_location(
                        file_path.stem, file_path
                    )
                    if spec is None:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Buscar funciones con decorador @tool
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (inspect.isfunction(obj) and 
                            hasattr(obj, '_is_tool') and 
                            obj._is_tool):
                            
                            self.tools[name] = obj
                            logger.debug(f"Herramienta dinámica cargada: {name}")
                            
                except Exception as e:
                    logger.error(f"Error cargando herramienta {file_path.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cargando herramientas dinámicas: {e}")
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Ejecuta una herramienta con los parámetros dados"""
        if tool_name not in self.tools:
            available = list(self.tools.keys())
            return f"Error: Herramienta '{tool_name}' no encontrada. Disponibles: {available}"
        
        try:
            tool_func = self.tools[tool_name]
            result = tool_func(**parameters)
            logger.debug(f"Herramienta ejecutada: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando herramienta {tool_name}: {e}")
            return f"Error ejecutando {tool_name}: {e}"

# ============================================================================
# GESTOR DE TAREAS
# ============================================================================

class TaskManager:
    """Gestor principal de tareas y ejecución del agente"""
    
    def __init__(self):
        self.model_manager: Optional[ModelManager] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.tool_manager: Optional[ToolManager] = None
        self.current_task = TaskContext()
        self.system_prompt_template = self._create_system_prompt()
    
    def initialize(self) -> bool:
        """Inicializa todos los componentes del sistema"""
        try:
            # Inicializar gestores
            self.tool_manager = ToolManager() # Initialize tool_manager first
            if not self.tool_manager.initialize(): # Load tools first
                logger.warning("Sistema de herramientas no disponible")
                return False # If tools can't be loaded, we can't proceed with Gemini
            
            self.model_manager = ModelManager(tool_manager=self.tool_manager) # Pass initialized tool_manager
            self.memory_manager = MemoryManager()
            
            # Configurar componentes
            if not self.model_manager.initialize():
                raise ModelNotAvailableError("No se pudo inicializar ningún modelo")
            
            if not self.memory_manager.initialize(self.model_manager):
                logger.warning("Sistema de memoria no disponible")
            
            if not self.tool_manager.initialize():
                logger.warning("Sistema de herramientas no disponible")
            
            logger.info("TaskManager inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando TaskManager: {e}")
            return False
    
    def _create_system_prompt(self) -> str:
        """Crea el prompt del sistema para el agente"""
        return """
Eres un asistente de programación autónomo y proactivo con memoria a largo plazo.

HERRAMIENTAS DISPONIBLES:
{available_tools}

INSTRUCCIONES:
1. Analiza la tarea del usuario y toma la iniciativa
2. Planifica paso a paso pero sé flexible
3. Ejecuta una herramienta a la vez
4. Aprende de tus errores y ajusta tu estrategia
5. Guarda información importante en memoria
6. Usa recursos del sistema de manera eficiente

FORMATO DE RESPUESTA:
Para usar una herramienta, responde EXACTAMENTE con:
```json
{{
  "tool_name": "nombre_de_la_herramienta",
  "parameters": {{
    "parametro1": "valor1",
    "parametro2": "valor2"
  }}
}}
```

MEMORIA RELEVANTE:
{relevant_memories}
"""
    
    def execute_task(self, user_prompt: str) -> None:
        """Ejecuta una tarea completa"""
        try:
            # Inicializar nueva tarea
            self.current_task.reset()
            self.current_task.task_id = str(uuid.uuid4())
            
            logger.info(f"Nueva tarea iniciada: {self.current_task.task_id}")
            
            # Recuperar memorias relevantes
            relevant_memories = ""
            if self.memory_manager:
                relevant_memories = self.memory_manager.retrieve_memories(user_prompt)
            
            # Preparar historial
            available_tools = list(self.tool_manager.tools.keys()) if self.tool_manager else []
            system_prompt = self.system_prompt_template.format(
                available_tools=available_tools,
                relevant_memories=relevant_memories
            )
            
            self.current_task.turn_history = [
                {'role': 'user', 'parts': [system_prompt, f"Tarea: {user_prompt}"]}
            ]
            
            # Ejecutar turnos
            self._execute_turns()
            
        except Exception as e:
            logger.error(f"Error ejecutando tarea: {e}")
            console.print(f"[red]Error: {e}[/red]")
    
    def _execute_turns(self):
        """Ejecuta los turnos de la tarea"""
        steps_remaining = CONFIG.MAX_STEPS_PER_TASK
        
        while steps_remaining > 0:
            try:
                step_num = CONFIG.MAX_STEPS_PER_TASK - steps_remaining + 1
                console.print(Panel(f"Paso {step_num}", title="[bold cyan]Ejecutando[/bold cyan]"))
                
                # Consultar modelo
                query_func = self.model_manager.get_query_function()
                model_name = (self.model_manager.gemini_model or 
                            self.model_manager.ollama_model)
                api_keys = self.model_manager.api_keys
                
                with console.status("[bold cyan]Pensando...[/bold cyan]"):
                    response = query_func(
                        self.current_task.turn_history, 
                        model_name, 
                        api_keys, 
                        step_num - 1
                    )
                
                # Parsear respuesta
                tool_call = self._parse_model_response(response)
                
                if tool_call:
                    # Ejecutar herramienta
                    result = self.tool_manager.execute_tool(
                        tool_call['tool_name'], 
                        tool_call['parameters']
                    )
                    
                    # Mostrar resultado
                    console.print(Panel(
                        result, 
                        title=f"[bold green]{tool_call['tool_name']}[/bold green]"
                    ))
                    
                    # Actualizar historial
                    self._update_history_with_tool_result(tool_call, result)
                    
                    # Verificar si la tarea está completa
                    if tool_call['tool_name'] == 'finish_task':
                        console.print(Panel(
                            "Tarea completada exitosamente", 
                            title="[bold green]¡Éxito![/bold green]"
                        ))
                        self.current_task.reset()
                        return
                    
                    # Verificar si se necesitan más pasos
                    elif tool_call['tool_name'] == 'request_more_steps':
                        steps_remaining += CONFIG.STEP_INCREMENT
                        console.print(f"[yellow]Pasos aumentados a {steps_remaining}[/yellow]")
                
                else:
                    # Respuesta de texto
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    console.print(Panel(response_text, title="[bold blue]Respuesta[/bold blue]"))
                    self.current_task.reset()
                    return
                
                steps_remaining -= 1
                
            except GeminiQuotaExceededError:
                logger.warning("Cuota de Gemini excedida, cambiando a Ollama")
                self.model_manager.current_provider = ModelProvider.OLLAMA
                continue
                
            except Exception as e:
                logger.error(f"Error en turno: {e}")
                console.print(f"[red]Error en turno: {e}[/red]")
                break
        
        console.print(Panel(
            "Se alcanzó el límite de pasos", 
            title="[bold red]Límite alcanzado[/bold red]"
        ))
        self.current_task.reset()
    
    def _parse_model_response(self, response):
        """Parsea la respuesta del modelo buscando llamadas a herramientas de forma robusta."""
        try:
            # Opción 1: Gemini con function calling nativo
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            tool_call = part.function_call
                            parameters = dict(tool_call.args) if hasattr(tool_call.args, 'items') else {}
                            return {
                                'tool_name': tool_call.name,
                                'parameters': parameters
                            }

            # Opción 2: Respuesta de texto con JSON (Ollama o Gemini fallback)
            response_text = getattr(response, 'text', str(response))
            
            # Extraer contenido JSON de bloques de código
            match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            json_string = match.group(1) if match else response_text
            
            # Limpiar el string JSON antes de parsear
            json_string = json_string.strip()
            
            # Si el string no parece un objeto JSON, no intentar parsear
            if not json_string.startswith('{'):
                return None

            # Parsear el JSON
            parsed_json = json.loads(json_string)
            
            # Validar la estructura del JSON
            if isinstance(parsed_json, dict) and 'tool_name' in parsed_json:
                # Asegurarse de que 'parameters' sea un diccionario
                if 'parameters' not in parsed_json or not isinstance(parsed_json['parameters'], dict):
                    parsed_json['parameters'] = {}
                return parsed_json

        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"No se pudo parsear la respuesta como llamada a herramienta: {e}")
        except Exception as e:
            logger.error(f"Error inesperado al parsear la respuesta del modelo: {e}")

        return None
    
    def _update_history_with_tool_result(self, tool_call: Dict, result: str):
        """Actualiza el historial con el resultado de una herramienta"""
        self.current_task.turn_history.append({
            'role': 'model',
            'parts': [f"Usando herramienta: {tool_call['tool_name']}"]
        })
        self.current_task.turn_history.append({
            'role': 'user',
            'parts': [f"Resultado: {result}"]
        })

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del asistente"""
    try:
        # Configurar argumentos
        parser = argparse.ArgumentParser(
            description=f"{CONFIG.APP_NAME} v{CONFIG.VERSION}"
        )
        parser.add_argument(
            "--version", 
            action="version", 
            version=f"%(prog)s {CONFIG.VERSION}"
        )
        args = parser.parse_args()
        
        # Mostrar banner
        console.print(Panel(
            f"[bold green]{CONFIG.APP_NAME} v{CONFIG.VERSION}[/bold green]\n"
            "Asistente autónomo con memoria a largo plazo",
            title="[bold blue]Iniciando[/bold blue]"
        ))
        
        # Inicializar sistema
        task_manager = TaskManager()
        
        if not task_manager.initialize():
            console.print("[red]Error: No se pudo inicializar el sistema[/red]")
            sys.exit(1)
        
        # Bucle principal
        console.print(Panel(
            "Escribe 'exit' o 'quit' para salir",
            title="[bold green]Listo[/bold green]"
        ))
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]¿Qué deseas hacer?[/bold green]")
                
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[yellow]¡Hasta luego![/yellow]")
                    break
                
                if user_input.strip():
                    task_manager.execute_task(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]¡Interrumpido! Saliendo...[/yellow]")
                break
            except Exception as e:
                logger.error(f"Error en bucle principal: {e}")
                console.print(f"[red]Error: {e}[/red]")
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        console.print(f"[red]Error crítico: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()