# Generador de Scripts para Plugins de QGIS

Este proyecto es una aplicación de escritorio en Python que permite a los usuarios crear e instalar plugins personalizados para QGIS mediante peticiones en lenguaje natural, ya sea por texto o por voz. Utiliza un sistema multiagente basado en CrewAI y modelos de IA de código abierto que se ejecutan localmente a través de Ollama.

## Características Principales

- **Interfaz Gráfica Intuitiva:** Desarrollada con PyQt5 para una experiencia de usuario sencilla.
- **Entrada por Voz:** Capacidad de grabar y transcribir automáticamente peticiones de voz utilizando Whisper AI.
- **Sistema Multiagente:** Un equipo de agentes de IA (Analista de Requisitos, Desarrollador de QGIS, Revisor y Empaquetador) colabora para generar el plugin.
- **IA Local:** Utiliza Ollama con el modelo `llama3:8b` para el procesamiento de lenguaje natural y la generación de código, asegurando privacidad y control.
- **Generación Completa:** Produce todos los archivos necesarios para un plugin funcional de QGIS.
- **Empaquetado Automático:** Genera archivos `.zip` listos para ser instalados directamente en QGIS.

## Requisitos del Sistema

Para ejecutar esta aplicación, asegúrate de cumplir con los siguientes requisitos:

- **Sistema Operativo:** Linux (Ubuntu 22.04 o superior recomendado), Windows 10+ o macOS 10.15+
- **Python:** Versión 3.9 o superior
- **Memoria RAM:** Mínimo 8GB (se recomienda 16GB o más para un rendimiento óptimo del modelo de IA)
- **Espacio en Disco:** Al menos 10GB de espacio libre en disco para la instalación de dependencias y modelos de IA
- **Micrófono:** Necesario para la funcionalidad de grabación de voz (opcional, la aplicación puede usarse solo con entrada de texto)

## Instalación

### 1. Clonar o Descargar el Proyecto

```bash
git clone <URL_DEL_REPOSITORIO>
cd generador-plugins-qgis
```

### 2. Instalar Ollama

Ollama es fundamental para ejecutar los modelos de lenguaje grandes (LLMs) localmente.

#### En Linux/macOS:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### En Windows:
Descarga el instalador desde [https://ollama.com/download](https://ollama.com/download)

### 3. Descargar el Modelo de Lenguaje

Una vez que Ollama esté instalado, descarga el modelo `llama3:8b`:

```bash
ollama run llama3:8b
```

### 4. Instalar Dependencias de Python

```bash
pip install -r requirements.txt
```

**Nota sobre `pyaudio`:** En algunos sistemas, la instalación de `pyaudio` puede requerir dependencias adicionales:

- **Ubuntu/Debian:**
  ```bash
  sudo apt-get install portaudio19-dev python3-pyaudio
  ```

- **macOS:**
  ```bash
  brew install portaudio
  ```

- **Windows:** Puede requerir Visual C++ Build Tools

## Ejecución

Una vez que todas las dependencias estén instaladas y Ollama esté configurado:

```bash
python main_app.py
```

## Uso de la Aplicación

La interfaz de usuario consta de los siguientes elementos:

- **Área de Texto:** Escribe la descripción del plugin de QGIS que deseas generar
- **Botón "🎤 Grabar Voz":** Graba tu voz describiendo el plugin
- **Botón "🔧 Generar Plugin":** Inicia el proceso de generación del plugin
- **Botón "🗑️ Limpiar":** Borra el contenido del área de texto y la consola
- **Consola de Salida:** Muestra el progreso y los resultados

### Proceso de Generación

1. **Describe tu Plugin:** Proporciona una descripción detallada del plugin que necesitas
2. **Generar:** Haz clic en "Generar Plugin"
3. **Resultado:** La consola te proporcionará la ruta al archivo `.zip` del plugin generado

## Arquitectura del Sistema

El sistema utiliza tres agentes especializados:

1. **Analista de Requisitos:** Analiza la petición del usuario y crea un plan técnico
2. **Desarrollador de QGIS:** Genera el código completo del plugin basado en PyQGIS
3. **Revisor y Empaquetador:** Revisa el código y crea el paquete final

## Solución de Problemas

- **Error de conexión con Ollama:** Asegúrate de que Ollama esté ejecutándose y el modelo esté descargado
- **Problemas con pyaudio:** Verifica que las dependencias de audio estén instaladas
- **Rendimiento lento:** La generación puede ser intensiva en recursos, considera cerrar otras aplicaciones

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o envía un pull request.

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

