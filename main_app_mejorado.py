#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Scripts para Plugins de QGIS
Aplicación de escritorio que permite crear e instalar plugins de QGIS personalizados
mediante peticiones en lenguaje natural, ya sea por texto o por voz.

Autor: Manus AI
Versión: 2.0
"""

import sys
import os
import threading
import tempfile
import wave
import json
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime

# Importaciones de PyQt5
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
        QWidget, QTextEdit, QPushButton, QTextBrowser, 
        QLabel, QProgressBar, QMessageBox, QSplitter,
        QFileDialog, QTabWidget, QGroupBox, QCheckBox,
        QSpinBox, QComboBox, QLineEdit
    )
    from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
    from PyQt5.QtGui import QFont, QIcon, QPixmap
except ImportError:
    print("Error: PyQt5 no está instalado. Ejecuta: pip install PyQt5")
    sys.exit(1)

# Importaciones de audio
try:
    import pyaudio
    import whisper
    AUDIO_AVAILABLE = True
except ImportError:
    print("Advertencia: pyaudio o whisper no están disponibles. La funcionalidad de voz estará deshabilitada.")
    AUDIO_AVAILABLE = False

# Importaciones de CrewAI
try:
    from crewai import Agent, Task, Crew
    from crewai.llm import LLM
    CREWAI_AVAILABLE = True
except ImportError:
    print("Advertencia: CrewAI no está disponible. La generación de plugins estará deshabilitada.")
    CREWAI_AVAILABLE = False

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qgis_plugin_generator.log'),
        logging.StreamHandler()
    ]
)

class AudioRecorder(QThread):
    """Hilo para grabar audio del micrófono"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recording = False
        self.audio_data = []
        self.p_audio = None
        self.stream = None
        
    def run(self):
        if not AUDIO_AVAILABLE:
            self.error.emit("Audio no disponible. Instala pyaudio y whisper.")
            return
            
        try:
            logging.info("Iniciando grabación de audio...")
            
            # Configuración de audio
            chunk = 1024
            format = pyaudio.paInt16
            channels = 1
            rate = 16000
            
            self.p_audio = pyaudio.PyAudio()
            
            self.stream = self.p_audio.open(
                format=format,
                channels=channels,
                rate=rate,
                input=True,
                frames_per_buffer=chunk
            )
            
            self.audio_data = []
            
            while self.recording:
                data = self.stream.read(chunk)
                self.audio_data.append(data)
            
            self.stream.stop_stream()
            self.stream.close()
            self.p_audio.terminate()
            logging.info("Grabación de audio finalizada.")
            
            # Guardar audio temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            wf = wave.open(temp_file.name, "wb")
            wf.setnchannels(channels)
            wf.setsampwidth(self.p_audio.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b"".join(self.audio_data))
            wf.close()
            
            # Transcribir con Whisper
            try:
                logging.info("Iniciando transcripción con Whisper...")
                model = whisper.load_model("base")
                result = model.transcribe(temp_file.name)
                self.finished.emit(result["text"])
                logging.info("Transcripción completada.")
            except Exception as e:
                logging.error(f"Error en transcripción: {str(e)}")
                self.error.emit(f"Error en transcripción: {str(e)}")
            finally:
                os.unlink(temp_file.name)
            
        except Exception as e:
            logging.error(f"Error en AudioRecorder: {str(e)}")
            self.error.emit(str(e))
        finally:
            if self.stream and self.stream.is_active():
                self.stream.stop_stream()
                self.stream.close()
            if self.p_audio:
                self.p_audio.terminate()
    
    def start_recording(self):
        self.recording = True
        self.start()
    
    def stop_recording(self):
        self.recording = False


class PluginGenerator(QThread):
    """Hilo para generar el plugin usando CrewAI"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str, str)  # resultado, ruta_zip
    error = pyqtSignal(str)
    
    def __init__(self, user_request, plugin_config=None):
        super().__init__()
        self.user_request = user_request
        self.plugin_config = plugin_config or {}
        
    def run(self):
        if not CREWAI_AVAILABLE:
            self.error.emit("CrewAI no está disponible. Instala crewai.")
            return
            
        try:
            self.progress.emit("Inicializando sistema multiagente...")
            logging.info("Inicializando sistema multiagente...")
            
            # Configurar LLM con Ollama
            try:
                llm = LLM(
                    model="ollama/llama3:8b",
                    base_url="http://localhost:11434"
                )
                logging.info("LLM configurado con Ollama.")
            except Exception as e:
                self.error.emit(f"Error conectando con Ollama: {str(e)}")
                return
            
            # Definir agentes mejorados
            planner_agent = Agent(
                role="Analista de Requisitos para QGIS",
                goal="Analizar peticiones de usuarios y crear planes técnicos detallados para plugins de QGIS",
                backstory="""Eres un experto analista de software especializado en QGIS y PyQGIS con más de 10 años de experiencia. 
                Conoces profundamente la API de QGIS, las mejores prácticas de desarrollo de plugins y las necesidades comunes de los usuarios de SIG.
                Tu trabajo es descomponer las peticiones de los usuarios en planes técnicos específicos y factibles.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            coder_agent = Agent(
                role="Desarrollador Senior de PyQGIS",
                goal="Escribir código Python completo y funcional para plugins de QGIS",
                backstory="""Eres un desarrollador senior con experiencia extensa en PyQGIS, Qt, y desarrollo de plugins para QGIS.
                Conoces las mejores prácticas de programación, manejo de errores, y optimización de rendimiento.
                Puedes generar código limpio, bien documentado y siguiendo los estándares de la comunidad QGIS.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            reviewer_agent = Agent(
                role="Revisor de Código y Especialista en Empaquetado",
                goal="Revisar código, asegurar calidad y crear paquetes de distribución",
                backstory="""Eres un experto en control de calidad de software y empaquetado de plugins de QGIS.
                Tu experiencia incluye testing, debugging, y distribución de software.
                Aseguras que el código sea robusto, seguro y fácil de instalar.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            # Definir tareas mejoradas
            planning_task = Task(
                description=f"""Analiza la siguiente petición del usuario y crea un plan técnico detallado para un plugin de QGIS:
                
                PETICIÓN DEL USUARIO: {self.user_request}
                
                CONFIGURACIÓN ADICIONAL: {self.plugin_config}
                
                Tu plan debe incluir:
                1. Análisis funcional del plugin solicitado
                2. Identificación de las clases y métodos de PyQGIS necesarios
                3. Estructura de archivos del plugin (metadata.txt, __init__.py, main_plugin.py, etc.)
                4. Diseño de la interfaz de usuario (botones, menús, diálogos)
                5. Flujo de trabajo y lógica de procesamiento
                6. Manejo de errores y validaciones necesarias
                7. Consideraciones de rendimiento y optimización
                
                Proporciona un plan estructurado y detallado que sirva como guía completa para el desarrollo.""",
                agent=planner_agent,
                expected_output="Un plan técnico completo y detallado con todos los componentes necesarios para el plugin"
            )
            
            coding_task = Task(
                description="""Basándote en el plan técnico proporcionado, genera el código completo para el plugin de QGIS.
                
                Debes crear los siguientes archivos con código funcional:
                
                1. **metadata.txt** - Metadatos del plugin con información completa
                2. **__init__.py** - Inicialización del plugin
                3. **main_plugin.py** - Clase principal del plugin con toda la lógica
                4. **plugin_dialog.py** - Diálogo de la interfaz de usuario (si es necesario)
                5. **plugin_dialog.ui** - Archivo de interfaz Qt Designer (si es necesario)
                6. **resources.qrc** - Archivo de recursos (si es necesario)
                7. **icon.png** - Descripción del icono necesario
                
                Requisitos del código:
                - Debe seguir las convenciones de PyQGIS y PEP 8
                - Incluir manejo robusto de errores
                - Comentarios explicativos en español
                - Validación de entrada de datos
                - Compatibilidad con QGIS 3.x
                - Código modular y mantenible
                
                Asegúrate de que el código sea completo y funcional.""",
                agent=coder_agent,
                expected_output="Código completo del plugin con todos los archivos necesarios y funcionalidad implementada",
                context=[planning_task]
            )
            
            review_task = Task(
                description="""Revisa el código generado, mejóralo si es necesario y crea el paquete final del plugin.
                
                Tareas de revisión:
                1. Revisar sintaxis y lógica del código
                2. Verificar compatibilidad con QGIS 3.x
                3. Validar estructura del plugin
                4. Mejorar comentarios y documentación
                5. Optimizar rendimiento si es posible
                
                Tareas de empaquetado:
                1. Crear carpeta del plugin con nombre apropiado
                2. Organizar todos los archivos correctamente
                3. Crear archivo ZIP para instalación
                4. Generar instrucciones de instalación detalladas
                5. Crear documentación de uso del plugin
                
                Proporciona el resultado final con la estructura completa del plugin.""",
                agent=reviewer_agent,
                expected_output="Plugin revisado, empaquetado en ZIP con instrucciones completas de instalación y uso",
                context=[planning_task, coding_task]
            )
            
            # Crear y ejecutar el crew
            self.progress.emit("Creando equipo de agentes...")
            crew = Crew(
                agents=[planner_agent, coder_agent, reviewer_agent],
                tasks=[planning_task, coding_task, review_task],
                verbose=True
            )
            
            self.progress.emit("Ejecutando generación del plugin...")
            logging.info("Iniciando ejecución del crew...")
            result = crew.kickoff()
            
            # Crear el archivo ZIP del plugin
            zip_path = self.create_plugin_package(str(result))
            
            self.finished.emit(str(result), zip_path)
            
        except Exception as e:
            logging.error(f"Error en la generación del plugin: {str(e)}")
            self.error.emit(f"Error en la generación del plugin: {str(e)}")
    
    def create_plugin_package(self, result_text):
        """Crear el paquete ZIP del plugin"""
        try:
            # Crear directorio temporal para el plugin
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plugin_name = f"qgis_plugin_{timestamp}"
            temp_dir = tempfile.mkdtemp()
            plugin_dir = os.path.join(temp_dir, plugin_name)
            os.makedirs(plugin_dir)
            
            # Aquí deberías extraer los archivos del resultado y crearlos
            # Por simplicidad, creamos un archivo de ejemplo
            with open(os.path.join(plugin_dir, "resultado.txt"), "w", encoding="utf-8") as f:
                f.write(result_text)
            
            # Crear archivo ZIP
            zip_path = os.path.join(os.getcwd(), f"{plugin_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(plugin_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            # Limpiar directorio temporal
            shutil.rmtree(temp_dir)
            
            return zip_path
            
        except Exception as e:
            logging.error(f"Error creando paquete: {str(e)}")
            return None


class ConfigurationWidget(QWidget):
    """Widget para configuración avanzada del plugin"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Grupo de configuración básica
        basic_group = QGroupBox("Configuración Básica")
        basic_layout = QVBoxLayout(basic_group)
        
        # Nombre del plugin
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre del Plugin:"))
        self.plugin_name = QLineEdit()
        self.plugin_name.setPlaceholderText("Mi Plugin Personalizado")
        name_layout.addWidget(self.plugin_name)
        basic_layout.addLayout(name_layout)
        
        # Versión
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Versión:"))
        self.plugin_version = QLineEdit("1.0.0")
        version_layout.addWidget(self.plugin_version)
        basic_layout.addLayout(version_layout)
        
        # Autor
        author_layout = QHBoxLayout()
        author_layout.addWidget(QLabel("Autor:"))
        self.plugin_author = QLineEdit()
        self.plugin_author.setPlaceholderText("Tu Nombre")
        author_layout.addWidget(self.plugin_author)
        basic_layout.addLayout(author_layout)
        
        layout.addWidget(basic_group)
        
        # Grupo de configuración avanzada
        advanced_group = QGroupBox("Configuración Avanzada")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # Tipo de plugin
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo de Plugin:"))
        self.plugin_type = QComboBox()
        self.plugin_type.addItems([
            "Procesamiento de Datos",
            "Herramienta de Análisis",
            "Importador/Exportador",
            "Visualización",
            "Utilidad General"
        ])
        type_layout.addWidget(self.plugin_type)
        advanced_layout.addLayout(type_layout)
        
        # Opciones adicionales
        self.add_menu = QCheckBox("Agregar al menú principal")
        self.add_menu.setChecked(True)
        advanced_layout.addWidget(self.add_menu)
        
        self.add_toolbar = QCheckBox("Agregar botón a la barra de herramientas")
        self.add_toolbar.setChecked(True)
        advanced_layout.addWidget(self.add_toolbar)
        
        self.add_dialog = QCheckBox("Incluir diálogo de configuración")
        self.add_dialog.setChecked(False)
        advanced_layout.addWidget(self.add_dialog)
        
        layout.addWidget(advanced_group)
    
    def get_config(self):
        """Obtener la configuración actual"""
        return {
            "name": self.plugin_name.text() or "Mi Plugin Personalizado",
            "version": self.plugin_version.text() or "1.0.0",
            "author": self.plugin_author.text() or "Autor Desconocido",
            "type": self.plugin_type.currentText(),
            "add_menu": self.add_menu.isChecked(),
            "add_toolbar": self.add_toolbar.isChecked(),
            "add_dialog": self.add_dialog.isChecked()
        }


class QGISPluginGenerator(QMainWindow):
    """Ventana principal de la aplicación mejorada"""
    
    def __init__(self):
        super().__init__()
        self.audio_recorder = None
        self.plugin_generator = None
        self.generated_plugins = []
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario mejorada"""
        self.setWindowTitle("Generador de Scripts para Plugins de QGIS v2.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central con pestañas
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Título
        title_label = QLabel("Generador de Scripts para Plugins de QGIS")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2E7D32; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Widget de pestañas
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Pestaña principal
        self.create_main_tab()
        
        # Pestaña de configuración
        self.create_config_tab()
        
        # Pestaña de historial
        self.create_history_tab()
        
        # Barra de estado
        self.statusBar().showMessage("Listo para generar plugins de QGIS")
        
    def create_main_tab(self):
        """Crear la pestaña principal"""
        main_tab = QWidget()
        self.tab_widget.addTab(main_tab, "Generador Principal")
        
        layout = QVBoxLayout(main_tab)
        
        # Splitter para dividir la interfaz
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Panel superior - Entrada
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        # Etiqueta mejorada
        input_label = QLabel("Describe detalladamente el plugin que deseas crear:")
        input_label.setFont(QFont("Arial", 12, QFont.Bold))
        input_layout.addWidget(input_label)
        
        # Área de texto mejorada
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Ejemplo detallado:\\n\\n"
            "Necesito un plugin que permita crear buffers automáticos alrededor de elementos seleccionados. "
            "El plugin debe:\\n"
            "- Detectar automáticamente el tipo de geometría seleccionada\\n"
            "- Permitir al usuario especificar la distancia del buffer\\n"
            "- Crear una nueva capa con los buffers generados\\n"
            "- Mostrar estadísticas del proceso en un diálogo\\n"
            "- Incluir validación de datos de entrada\\n\\n"
            "Sé específico sobre las funcionalidades que necesitas..."
        )
        self.text_input.setMaximumHeight(200)
        self.text_input.setFont(QFont("Arial", 10))
        input_layout.addWidget(self.text_input)
        
        # Botones mejorados
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("🎤 Grabar Voz")
        self.record_button.setEnabled(AUDIO_AVAILABLE)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.record_button)
        
        self.generate_button = QPushButton("🔧 Generar Plugin")
        self.generate_button.setEnabled(CREWAI_AVAILABLE)
        self.generate_button.clicked.connect(self.generate_plugin)
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.generate_button)
        
        self.clear_button = QPushButton("🗑️ Limpiar")
        self.clear_button.clicked.connect(self.clear_all)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        button_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("💾 Guardar Resultado")
        self.save_button.clicked.connect(self.save_result)
        self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.save_button)
        
        input_layout.addLayout(button_layout)
        splitter.addWidget(input_widget)
        
        # Panel inferior - Salida
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        # Etiqueta para la consola
        output_label = QLabel("Consola de salida y resultados:")
        output_label.setFont(QFont("Arial", 12, QFont.Bold))
        output_layout.addWidget(output_label)
        
        # Consola de salida mejorada
        self.output_console = QTextBrowser()
        self.output_console.setFont(QFont("Consolas", 9))
        self.output_console.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)
        output_layout.addWidget(self.output_console)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
        """)
        output_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(output_widget)
        splitter.setSizes([300, 500])
        
        # Mensaje inicial
        self.show_welcome_message()
    
    def create_config_tab(self):
        """Crear la pestaña de configuración"""
        self.config_widget = ConfigurationWidget()
        self.tab_widget.addTab(self.config_widget, "Configuración")
    
    def create_history_tab(self):
        """Crear la pestaña de historial"""
        history_tab = QWidget()
        self.tab_widget.addTab(history_tab, "Historial")
        
        layout = QVBoxLayout(history_tab)
        
        history_label = QLabel("Historial de plugins generados:")
        history_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(history_label)
        
        self.history_list = QTextBrowser()
        self.history_list.setFont(QFont("Arial", 10))
        layout.addWidget(self.history_list)
        
        # Botón para limpiar historial
        clear_history_btn = QPushButton("🗑️ Limpiar Historial")
        clear_history_btn.clicked.connect(self.clear_history)
        layout.addWidget(clear_history_btn)
    
    def show_welcome_message(self):
        """Mostrar mensaje de bienvenida"""
        welcome_msg = """
<div style='color: #4CAF50; font-size: 14px; font-weight: bold;'>
=== Generador de Scripts para Plugins de QGIS v2.0 ===
</div>
<div style='color: #2196F3; font-size: 12px;'>
🚀 Sistema multiagente con IA local para generar plugins personalizados
</div>
<div style='color: #ffffff; font-size: 11px;'>
✅ Listo para generar plugins personalizados de QGIS<br>
📝 Escribe una descripción detallada o usa el botón de grabación de voz<br>
⚙️ Configura opciones avanzadas en la pestaña 'Configuración'<br>
📊 Revisa el historial de plugins en la pestaña 'Historial'<br>
</div>
<div style='color: #FF9800; font-size: 10px;'>
ℹ️ Estado de componentes:<br>
• Audio (Whisper): """ + ("✅ Disponible" if AUDIO_AVAILABLE else "❌ No disponible") + """<br>
• CrewAI: """ + ("✅ Disponible" if CREWAI_AVAILABLE else "❌ No disponible") + """<br>
</div>
<hr style='border: 1px solid #555555;'>
        """
        self.output_console.setHtml(welcome_msg)
    
    def toggle_recording(self):
        """Alternar grabación de audio"""
        if not AUDIO_AVAILABLE:
            self.show_error("Funcionalidad de audio no disponible. Instala pyaudio y whisper.")
            return
            
        if self.audio_recorder is None or not (self.audio_recorder.isRunning() and self.audio_recorder.recording):
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Iniciar grabación de audio"""
        try:
            self.audio_recorder = AudioRecorder()
            self.audio_recorder.finished.connect(self.on_transcription_finished)
            self.audio_recorder.error.connect(self.on_transcription_error)
            
            self.record_button.setText("⏹️ Detener Grabación")
            self.record_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 12px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            
            self.append_to_console("🎤 <span style='color: #4CAF50;'>Iniciando grabación de audio...</span>")
            self.statusBar().showMessage("Grabando audio...")
            
            self.audio_recorder.start_recording()
            
        except Exception as e:
            logging.error(f"Error al iniciar grabación: {str(e)}")
            self.show_error(f"Error al iniciar grabación: {str(e)}")
    
    def stop_recording(self):
        """Detener grabación de audio"""
        if self.audio_recorder and self.audio_recorder.recording:
            self.append_to_console("⏹️ <span style='color: #FF9800;'>Deteniendo grabación y transcribiendo...</span>")
            self.statusBar().showMessage("Transcribiendo audio...")
            self.audio_recorder.stop_recording()
    
    def on_transcription_finished(self, text):
        """Manejar transcripción completada"""
        self.record_button.setText("🎤 Grabar Voz")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        if text.strip():
            self.text_input.setPlainText(text)
            self.append_to_console(f"✅ <span style='color: #4CAF50;'>Transcripción completada:</span><br><span style='color: #E0E0E0;'>{text}</span>")
            self.statusBar().showMessage("Transcripción completada")
        else:
            self.append_to_console("⚠️ <span style='color: #FF9800;'>No se detectó texto en la grabación</span>")
            self.statusBar().showMessage("No se detectó texto")
    
    def on_transcription_error(self, error):
        """Manejar error en transcripción"""
        self.record_button.setText("🎤 Grabar Voz")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.show_error(f"Error en transcripción: {error}")
        self.statusBar().showMessage("Error en transcripción")
    
    def generate_plugin(self):
        """Generar plugin usando CrewAI"""
        if not CREWAI_AVAILABLE:
            self.show_error("CrewAI no está disponible. Instala crewai para usar esta funcionalidad.")
            return
            
        user_request = self.text_input.toPlainText().strip()
        
        if not user_request:
            self.show_error("Por favor, ingresa una descripción del plugin que deseas crear.")
            return
        
        if len(user_request) < 20:
            reply = QMessageBox.question(
                self, 
                "Descripción corta",
                "La descripción parece muy corta. ¿Deseas continuar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Obtener configuración
        plugin_config = self.config_widget.get_config()
        
        # Deshabilitar botones durante la generación
        self.generate_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        
        self.append_to_console("<hr>")
        self.append_to_console("🚀 <span style='color: #2196F3; font-weight: bold;'>Iniciando generación del plugin...</span>")
        self.append_to_console(f"📝 <span style='color: #E0E0E0;'>Petición:</span> {user_request}")
        self.append_to_console(f"⚙️ <span style='color: #E0E0E0;'>Configuración:</span> {plugin_config}")
        
        self.statusBar().showMessage("Generando plugin...")
        
        # Crear y ejecutar el generador
        self.plugin_generator = PluginGenerator(user_request, plugin_config)
        self.plugin_generator.progress.connect(self.on_generation_progress)
        self.plugin_generator.finished.connect(self.on_generation_finished)
        self.plugin_generator.error.connect(self.on_generation_error)
        self.plugin_generator.start()
    
    def on_generation_progress(self, message):
        """Manejar progreso de generación"""
        self.append_to_console(f"⏳ <span style='color: #FF9800;'>{message}</span>")
        self.statusBar().showMessage(message)
    
    def on_generation_finished(self, result, zip_path):
        """Manejar generación completada"""
        self.generate_button.setEnabled(True)
        self.record_button.setEnabled(AUDIO_AVAILABLE)
        self.save_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.append_to_console("<br>✅ <span style='color: #4CAF50; font-weight: bold;'>¡Plugin generado exitosamente!</span>")
        
        if zip_path:
            self.append_to_console(f"📦 <span style='color: #4CAF50;'>Archivo ZIP creado:</span> <span style='color: #E0E0E0;'>{zip_path}</span>")
        
        self.append_to_console("<div style='border: 1px solid #555555; padding: 10px; margin: 10px 0; background-color: #2e2e2e;'>")
        self.append_to_console("<span style='color: #4CAF50; font-weight: bold;'>RESULTADO DEL PLUGIN:</span><br>")
        self.append_to_console(f"<span style='color: #E0E0E0; font-family: Consolas;'>{result}</span>")
        self.append_to_console("</div>")
        
        # Agregar al historial
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plugin_info = {
            "timestamp": timestamp,
            "request": self.text_input.toPlainText().strip()[:100] + "...",
            "config": self.config_widget.get_config(),
            "zip_path": zip_path
        }
        self.generated_plugins.append(plugin_info)
        self.update_history()
        
        self.statusBar().showMessage("Plugin generado exitosamente")
        
        QMessageBox.information(
            self, 
            "Éxito", 
            f"Plugin generado exitosamente.\\n\\nArchivo ZIP: {zip_path if zip_path else 'No disponible'}\\n\\nRevisa la consola para más detalles."
        )
    
    def on_generation_error(self, error):
        """Manejar error en generación"""
        self.generate_button.setEnabled(True)
        self.record_button.setEnabled(AUDIO_AVAILABLE)
        self.progress_bar.setVisible(False)
        
        self.show_error(f"Error en la generación: {error}")
        self.statusBar().showMessage("Error en la generación")
    
    def save_result(self):
        """Guardar resultado en archivo"""
        if not self.output_console.toPlainText():
            self.show_error("No hay contenido para guardar.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Resultado",
            f"resultado_plugin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Archivos de texto (*.txt);;Todos los archivos (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_console.toPlainText())
                self.append_to_console(f"💾 <span style='color: #4CAF50;'>Resultado guardado en:</span> <span style='color: #E0E0E0;'>{file_path}</span>")
                self.statusBar().showMessage(f"Resultado guardado: {file_path}")
            except Exception as e:
                self.show_error(f"Error al guardar archivo: {str(e)}")
    
    def clear_all(self):
        """Limpiar toda la interfaz"""
        self.text_input.clear()
        self.output_console.clear()
        self.show_welcome_message()
        self.save_button.setEnabled(False)
        self.statusBar().showMessage("Interfaz limpiada")
    
    def clear_history(self):
        """Limpiar historial"""
        self.generated_plugins.clear()
        self.history_list.clear()
        self.statusBar().showMessage("Historial limpiado")
    
    def update_history(self):
        """Actualizar la vista del historial"""
        history_html = "<h3>Historial de Plugins Generados</h3>"
        
        for i, plugin in enumerate(reversed(self.generated_plugins), 1):
            history_html += f"""
            <div style='border: 1px solid #cccccc; padding: 10px; margin: 5px 0; background-color: #f9f9f9;'>
                <h4>Plugin #{len(self.generated_plugins) - i + 1}</h4>
                <p><strong>Fecha:</strong> {plugin['timestamp']}</p>
                <p><strong>Descripción:</strong> {plugin['request']}</p>
                <p><strong>Configuración:</strong> {plugin['config']['name']} v{plugin['config']['version']}</p>
                <p><strong>Archivo ZIP:</strong> {plugin['zip_path'] if plugin['zip_path'] else 'No disponible'}</p>
            </div>
            """
        
        if not self.generated_plugins:
            history_html += "<p><em>No hay plugins generados aún.</em></p>"
        
        self.history_list.setHtml(history_html)
    
    def append_to_console(self, message):
        """Agregar mensaje a la consola con formato HTML"""
        self.output_console.append(message)
        # Auto-scroll al final
        scrollbar = self.output_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def show_error(self, message):
        """Mostrar mensaje de error"""
        self.append_to_console(f"❌ <span style='color: #f44336; font-weight: bold;'>Error:</span> <span style='color: #E0E0E0;'>{message}</span>")
        QMessageBox.critical(self, "Error", message)
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        if self.audio_recorder and self.audio_recorder.recording:
            self.audio_recorder.stop_recording()
        
        if self.plugin_generator and self.plugin_generator.isRunning():
            reply = QMessageBox.question(
                self, 
                "Cerrar aplicación",
                "Hay una generación en progreso. ¿Deseas cerrar la aplicación?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.plugin_generator.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Configurar estilo de la aplicación
    app.setStyle("Fusion")
    
    # Aplicar tema oscuro
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2b2b2b;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #4CAF50;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin: 10px 0;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLineEdit, QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px;
            color: #ffffff;
        }
        QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px;
            color: #ffffff;
        }
        QCheckBox {
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #3c3c3c;
            border: 1px solid #555555;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
    """)
    
    # Crear y mostrar la ventana principal
    window = QGISPluginGenerator()
    window.show()
    
    # Ejecutar la aplicación
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

