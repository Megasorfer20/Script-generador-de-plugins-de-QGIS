#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Scripts para Plugins de QGIS
Aplicación de escritorio que permite crear e instalar plugins de QGIS personalizados
mediante peticiones en lenguaje natural, ya sea por texto o por voz.
"""

import sys
import os
import threading
import tempfile
import wave
import pyaudio
import whisper
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTextEdit, QPushButton, QTextBrowser, 
                             QLabel, QProgressBar, QMessageBox, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
from crewai import Agent, Task, Crew
from crewai.llm import LLM
import zipfile
import json
import shutil
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class AudioRecorder(QThread):
    """Hilo para grabar audio del micrófono"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recording = False
        self.audio_data = []
        self.p_audio = None # Initialize PyAudio instance
        self.stream = None # Initialize audio stream
        
    def run(self):
        try:
            logging.info("Iniciando grabación de audio...")
            # Configuración de audio
            chunk = 1024
            format = pyaudio.paInt16
            channels = 1
            rate = 16000
            
            self.p_audio = pyaudio.PyAudio()
            
            self.stream = self.p_audio.open(format=format,
                          channels=channels,
                          rate=rate,
                          input=True,
                          frames_per_buffer=chunk)
            
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
            logging.info(f"Audio guardado temporalmente en: {temp_file.name}")
            
            # Transcribir con Whisper
            try:
                logging.info("Iniciando transcripción con Whisper...")
                model = whisper.load_model("base")
                result = model.transcribe(temp_file.name)
                self.finished.emit(result["text"])
                logging.info("Transcripción con Whisper completada.")
            except Exception as e:
                logging.error(f"Error al cargar o transcribir con Whisper: {str(e)}")
                self.error.emit(f"Error al cargar o transcribir con Whisper: {str(e)}")
            finally:
                # Limpiar archivo temporal
                os.unlink(temp_file.name)
                logging.info(f"Archivo temporal {temp_file.name} eliminado.")
            
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
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, user_request):
        super().__init__()
        self.user_request = user_request
        
    def run(self):
        try:
            self.progress.emit("Inicializando sistema multiagente...")
            logging.info("Inicializando sistema multiagente...")
            
            # Configurar LLM con Ollama
            llm = LLM(
                model="ollama/llama3:8b",
                base_url="http://localhost:11434"
            )
            logging.info("LLM configurado con Ollama.")
            
            # Definir agentes
            planner_agent = Agent(
                role="Analista de Requisitos",
                goal="Analizar la petición del usuario y crear un plan técnico detallado para el plugin de QGIS",
                backstory="""Eres un experto analista de software especializado en QGIS y PyQGIS. 
                Tu trabajo es descomponer las peticiones de los usuarios en planes técnicos específicos 
                que incluyan las funciones de PyQGIS necesarias, la estructura de archivos del plugin 
                y los elementos de la interfaz de usuario.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            coder_agent = Agent(
                role="Desarrollador de QGIS",
                goal="Escribir el código Python completo para el plugin de QGIS basándose en el plan técnico",
                backstory="""Eres un desarrollador senior especializado en PyQGIS con amplio conocimiento 
                de la API de QGIS, la estructura de plugins y las mejores prácticas de desarrollo. 
                Puedes generar código completo y funcional para plugins de QGIS.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            
            reviewer_agent = Agent(
                role="Revisor de Código y Empaquetador",
                goal="Revisar el código generado, asegurar su calidad y empaquetarlo para despliegue",
                backstory="""Eres un experto en control de calidad de software y empaquetado de plugins de QGIS. 
                Tu trabajo es revisar el código en busca de errores, asegurar que sigue las mejores prácticas 
                y crear el paquete final listo para instalación.""",
                verbose=True,
                allow_delegation=False,
                llm=llm
            )
            logging.info("Agentes definidos.")
            
            # Definir tareas
            planning_task = Task(
                description=f"""Analiza la siguiente petición del usuario y crea un plan técnico detallado:
                
                PETICIÓN: {self.user_request}
                
                Tu plan debe incluir:
                1. Descripción funcional del plugin
                2. Funciones de PyQGIS necesarias
                3. Estructura de archivos del plugin
                4. Elementos de la interfaz de usuario
                5. Pasos específicos para el desarrollo
                
                Proporciona un plan claro y estructurado que el desarrollador pueda seguir.""",
                agent=planner_agent,
                expected_output="Un plan técnico detallado con todos los componentes necesarios para el plugin"
            )
            
            coding_task = Task(
                description="""Basándote en el plan técnico proporcionado, genera el código completo para el plugin de QGIS.
                
                Debes crear los siguientes archivos:
                1. metadata.txt - Metadatos del plugin
                2. __init__.py - Inicialización del plugin
                3. main_plugin.py - Lógica principal del plugin
                4. plugin_dialog.ui - Interfaz de usuario (si es necesaria)
                5. resources.qrc - Recursos del plugin (si es necesario)
                
                Asegúrate de que el código:
                - Siga las convenciones de PyQGIS
                - Sea funcional y completo
                - Incluya manejo de errores
                - Tenga comentarios explicativos""",
                agent=coder_agent,
                expected_output="Código completo del plugin con todos los archivos necesarios",
                context=[planning_task]
            )
            
            review_task = Task(
                description="""Revisa el código generado y crea el paquete final del plugin.
                
                Tareas a realizar:
                1. Revisar el código en busca de errores de sintaxis y lógicos
                2. Verificar que sigue la estructura correcta de un plugin de QGIS
                3. Crear una carpeta con el nombre del plugin
                4. Organizar todos los archivos en la carpeta
                5. Crear un archivo ZIP listo para instalación
                6. Proporcionar instrucciones de instalación
                
                Entrega el resultado final con la ruta del archivo ZIP y las instrucciones.""",
                agent=reviewer_agent,
                expected_output="Plugin empaquetado en ZIP con instrucciones de instalación",
                context=[planning_task, coding_task]
            )
            logging.info("Tareas definidas.")
            
            # Crear y ejecutar el crew
            self.progress.emit("Creando equipo de agentes...")
            crew = Crew(
                agents=[planner_agent, coder_agent, reviewer_agent],
                tasks=[planning_task, coding_task, review_task],
                verbose=True
            )
            logging.info("Equipo de agentes creado.")
            
            self.progress.emit("Ejecutando generación del plugin...")
            logging.info("Iniciando ejecución del crew...")
            result = crew.kickoff()
            logging.info("Ejecución del crew finalizada.")
            
            self.finished.emit(str(result))
            
        except Exception as e:
            logging.error(f"Error en la generación del plugin: {str(e)}")
            self.error.emit(f"Error en la generación del plugin: {str(e)}")


class QGISPluginGenerator(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        self.audio_recorder = None
        self.plugin_generator = None
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        self.setWindowTitle("Generador de Scripts para Plugins de QGIS")
        self.setGeometry(100, 100, 1000, 700)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Título
        title_label = QLabel("Generador de Scripts para Plugins de QGIS")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Splitter para dividir la interfaz
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Panel superior - Entrada de texto
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        # Etiqueta para el área de texto
        input_label = QLabel("Describe el plugin que deseas crear:")
        input_layout.addWidget(input_label)
        
        # Área de texto para la petición
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Ejemplo: Necesito un plugin que cree una capa de buffer de 100 metros "
            "alrededor de los puntos seleccionados en la capa activa..."
        )
        self.text_input.setMaximumHeight(150)
        input_layout.addWidget(self.text_input)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("🎤 Grabar Voz")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)
        
        self.generate_button = QPushButton("🔧 Generar Plugin")
        self.generate_button.clicked.connect(self.generate_plugin)
        button_layout.addWidget(self.generate_button)
        
        self.clear_button = QPushButton("🗑️ Limpiar")
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)
        
        input_layout.addLayout(button_layout)
        splitter.addWidget(input_widget)
        
        # Panel inferior - Consola de salida
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        # Etiqueta para la consola
        output_label = QLabel("Consola de salida:")
        output_layout.addWidget(output_label)
        
        # Consola de salida
        self.output_console = QTextBrowser()
        self.output_console.setFont(QFont("Courier", 9))
        output_layout.addWidget(self.output_console)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        output_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(output_widget)
        
        # Configurar proporciones del splitter
        splitter.setSizes([250, 450])
        
        # Mensaje inicial
        self.output_console.append("=== Generador de Scripts para Plugins de QGIS ===")
        self.output_console.append("Listo para generar plugins personalizados.")
        self.output_console.append("Escribe tu petición o usa el botón de grabación de voz.\n")
        
    def toggle_recording(self):
        """Alternar grabación de audio"""
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
            self.record_button.setStyleSheet("background-color: #ff4444;")
            self.output_console.append("🎤 Iniciando grabación de audio...")
            logging.info("Botón de grabación presionado: Iniciando grabación.")
            
            self.audio_recorder.start_recording()
            
        except Exception as e:
            logging.error(f"Error al iniciar grabación desde GUI: {str(e)}")
            self.show_error(f"Error al iniciar grabación: {str(e)}")
    
    def stop_recording(self):
        """Detener grabación de audio"""
        if self.audio_recorder and self.audio_recorder.recording:
            self.output_console.append("⏹️ Deteniendo grabación y transcribiendo...")
            logging.info("Botón de grabación presionado: Deteniendo grabación.")
            self.audio_recorder.stop_recording()
    
    def on_transcription_finished(self, text):
        """Manejar transcripción completada"""
        self.record_button.setText("🎤 Grabar Voz")
        self.record_button.setStyleSheet("")
        
        if text.strip():
            self.text_input.setPlainText(text)
            self.output_console.append(f"✅ Transcripción completada: {text}")
            logging.info(f"Transcripción exitosa: {text[:50]}...")
        else:
            self.output_console.append("⚠️ No se detectó texto en la grabación")
            logging.warning("Transcripción completada pero no se detectó texto.")
    
    def on_transcription_error(self, error):
        """Manejar error en transcripción"""
        self.record_button.setText("🎤 Grabar Voz")
        self.record_button.setStyleSheet("")
        logging.error(f"Error en transcripción: {error}")
        self.show_error(f"Error en transcripción: {error}")
    
    def generate_plugin(self):
        """Generar plugin usando CrewAI"""
        user_request = self.text_input.toPlainText().strip()
        
        if not user_request:
            self.show_error("Por favor, ingresa una descripción del plugin que deseas crear.")
            logging.warning("Intento de generación de plugin sin petición de usuario.")
            return
        
        # Deshabilitar botones durante la generación
        self.generate_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Progreso indeterminado
        
        self.output_console.append(f"\n🚀 Iniciando generación del plugin...")
        self.output_console.append(f"📝 Petición: {user_request}\n")
        logging.info(f"Iniciando generación de plugin para la petición: {user_request[:100]}...")
        
        # Crear y ejecutar el generador
        self.plugin_generator = PluginGenerator(user_request)
        self.plugin_generator.progress.connect(self.on_generation_progress)
        self.plugin_generator.finished.connect(self.on_generation_finished)
        self.plugin_generator.error.connect(self.on_generation_error)
        self.plugin_generator.start()
    
    def on_generation_progress(self, message):
        """Manejar progreso de generación"""
        self.output_console.append(f"⏳ {message}")
        logging.info(f"Progreso de generación: {message}")
    
    def on_generation_finished(self, result):
        """Manejar generación completada"""
        self.generate_button.setEnabled(True)
        self.record_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.output_console.append("\n✅ ¡Plugin generado exitosamente!")
        self.output_console.append("=" * 50)
        self.output_console.append(result)
        self.output_console.append("=" * 50)
        logging.info("Generación de plugin completada exitosamente.")
        
        QMessageBox.information(self, "Éxito", "Plugin generado exitosamente. Revisa la consola para más detalles.")
    
    def on_generation_error(self, error):
        """Manejar error en generación"""
        self.generate_button.setEnabled(True)
        self.record_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        logging.error(f"Error en la generación: {error}")
        self.show_error(f"Error en la generación: {error}")
    
    def clear_all(self):
        """Limpiar toda la interfaz"""
        self.text_input.clear()
        self.output_console.clear()
        self.output_console.append("=== Generador de Scripts para Plugins de QGIS ===")
        self.output_console.append("Interfaz limpiada. Listo para nueva petición.\n")
        logging.info("Interfaz de usuario limpiada.")
    
    def show_error(self, message):
        """Mostrar mensaje de error"""
        self.output_console.append(f"❌ Error: {message}")
        QMessageBox.critical(self, "Error", message)
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        if self.audio_recorder and self.audio_recorder.recording:
            self.audio_recorder.stop_recording()
            logging.info("Deteniendo grabación de audio al cerrar la aplicación.")
        
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
                logging.info("Terminando generación de plugin al cerrar la aplicación.")
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
    
    # Crear y mostrar la ventana principal
    window = QGISPluginGenerator()
    window.show()
    
    # Ejecutar la aplicación
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



