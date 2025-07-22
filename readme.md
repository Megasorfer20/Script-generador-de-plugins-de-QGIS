# Generador de Plugins para QGIS con IA (v3.0)

Esta aplicación de escritorio permite generar plugins para QGIS a partir de descripciones en lenguaje natural (texto o voz), utilizando un sistema de agentes de IA (CrewAI) que se ejecuta localmente.

## Requisitos Previos

Para que el script funcione correctamente en **Windows**, necesitas tener lo siguiente:

1.  **Python 3.8+**: Asegúrate de tener Python instalado. Puedes descargarlo desde [python.org](https://www.python.org/ ). Durante la instalación, **marca la casilla "Add Python to PATH"**.
2.  **Ollama**: Un motor para ejecutar modelos de lenguaje grandes (LLMs) localmente.
    *   Descarga e instala Ollama desde [ollama.com](https://ollama.com/ ).
    *   Una vez instalado, abre una terminal (CMD o PowerShell) y ejecuta el siguiente comando para descargar el modelo que usaremos:
        ```bash
        ollama pull llama3:8b
        ```
    *   Ollama debe estar ejecutándose en segundo plano para que el script funcione.

## Guía de Instalación Detallada

Sigue estos pasos en orden para configurar tu entorno.

### Paso 1: Crear un Entorno Virtual

Es una buena práctica aislar las dependencias de este proyecto. Abre una terminal (CMD o PowerShell) en la carpeta donde guardaste `generador_qgis_v3.py`.

```bash
# 1. Crea un entorno virtual llamado 'venv'
python -m venv venv

# 2. Activa el entorno virtual
.\venv\Scripts\activate
```

Verás `(venv)` al principio de la línea de tu terminal, lo que indica que el entorno está activo.

### Paso 2: Instalar las Dependencias de Python

Con el entorno virtual activo, instala todas las librerías necesarias ejecutando los siguientes comandos uno por uno.

```bash
# 1. PyQt5 para la interfaz gráfica
pip install PyQt5

# 2. CrewAI y sus dependencias para el sistema de IA
pip install crewai

# 3. PyAudio para la grabación de voz (requiere un paso especial)
#    Instalaremos desde un "wheel" pre-compilado para evitar errores comunes en Windows.
#    Descarga el wheel correspondiente a tu versión de Python y arquitectura (32 o 64 bits) desde:
#    https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
#    Ejemplo para Python 3.10 de 64 bits, el archivo sería: PyAudio-0.2.14-cp310-cp310-win_amd64.whl
#    Una vez descargado, instálalo (asegúrate de estar en la carpeta de descargas o usa la ruta completa ):
pip install PyAudio-0.2.14-cp310-cp310-win_amd64.whl

# 4. OpenAI-Whisper para la transcripción de voz a texto
pip install openai-whisper

# 5. (Opcional pero recomendado) Pytorch para acelerar Whisper
pip install torch
```

## Cómo Ejecutar la Aplicación

1.  **Inicia Ollama**: Asegúrate de que la aplicación de Ollama se esté ejecutando en tu sistema.
2.  **Activa el Entorno Virtual**: Si aún no lo has hecho, abre una terminal en la carpeta del proyecto y ejecuta:
    ```bash
    .\venv\Scripts\activate
    ```
3.  **Ejecuta el Script**:
    ```bash
    python generador_qgis_v3.py
    ```

Se abrirá la ventana de la aplicación.

## Cómo Usar la Aplicación

1.  **Configura tu Plugin**: Ve a la pestaña **Configuración** y escribe un nombre para tu plugin (ej. `MiPluginDeCapas`). Este nombre se usará para la carpeta y el archivo `.zip`.
2.  **Describe tu Idea**: En la pestaña **Generador**, escribe una descripción clara y detallada de lo que quieres que haga el plugin.
    *   **Ejemplo Bueno**: "Necesito un plugin que añada un botón a la barra de herramientas. Al hacer clic, debe pedir al usuario que seleccione una capa vectorial de polígonos. Luego, debe calcular el área de cada polígono y añadirla a una nueva columna llamada 'AREA_CALC' en la tabla de atributos."
    *   **Ejemplo Malo**: "hacer un plugin de áreas"
3.  **Genera el Plugin**: Haz clic en el botón **🚀 Generar Plugin**.
4.  **Espera**: El proceso puede tardar varios minutos. La consola de salida te mostrará el progreso. **No cierres la aplicación**.
5.  **Encuentra tu Plugin**: Una vez completado, aparecerá un mensaje de éxito. El plugin se guardará como un archivo `.zip` dentro de una nueva carpeta llamada `generated_plugins`, que se creará en el mismo lugar donde ejecutaste el script. La ruta completa aparecerá en la consola.

## Cómo Instalar el Plugin en QGIS

1.  Abre QGIS.
2.  Ve al menú **Complementos > Administrar e instalar complementos...**.
3.  En la ventana de complementos, selecciona la opción **Instalar a partir de ZIP**.
4.  Haz clic en el botón `...` y busca el archivo `.zip` que generó la aplicación.
5.  Haz clic en **Instalar complemento**.

¡Listo! Tu plugin debería estar instalado y activo en QGIS.
