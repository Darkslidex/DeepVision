# Archivo: core/controller.py
import cv2
import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import numpy as np
from core.ai.detection_worker import DetectionWorker
from core.logic.logic_worker import LogicWorker

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    stopped_signal = pyqtSignal()

    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self._run_flag = True

    def run(self):
        # Intentar abrir la cámara (0 si es webcam, string si es RTSP)
        src = 0 if str(self.rtsp_url) == "0" else self.rtsp_url
        cap = cv2.VideoCapture(src)
        
        while self._run_flag:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
            else:
                # Si falla la lectura, esperamos un poco
                time.sleep(0.1)
        
        # Limpieza al salir
        cap.release()
        self.stopped_signal.emit()

    def stop(self):
        self._run_flag = False
        self.wait()

class SystemController(QObject):
    # Señales hacia la UI
    frame_signal = pyqtSignal(object)       # Envía la imagen
    detections_signal = pyqtSignal(list)    # Envía cajas de detección (Fase 2)
    log_signal = pyqtSignal(str)            # Envía mensajes de log
    alarm_signal = pyqtSignal(str, str, str)# Level, Type, Message
    bucket_status_signal = pyqtSignal(float, float) # Current, Capacity
    video_stopped_signal = pyqtSignal()     # ¡ESTA ES LA SEÑAL QUE FALTABA!
    
    def __init__(self):
        super().__init__()
        self.thread = None
        self.monitoring_active = False
        
        # Workers
        self.detection_worker = None
        self.logic_worker = LogicWorker()
        
        # Conectar señales de lógica a sistema (alarmas)
        self.logic_worker.alarm_signal.connect(self.alarm_signal.emit)
        self.logic_worker.bucket_status_signal.connect(self.bucket_status_signal.emit)

    def process_frame(self, frame):
        if not self.monitoring_active:
            return
        # Enviar frame procesado a la UI
        self.frame_signal.emit(frame)
        
        # Enviar frame a detección
        if self.detection_worker and self.detection_worker.is_running:
            self.detection_worker.add_frame(frame)

    @pyqtSlot(str)
    def switch_camera(self, url):
        self.stop_video() # Detener anterior primero
        self.log_signal.emit(f"Conectando cámara...")
        
        # Crear nuevo hilo de VIDEO
        self.thread = VideoThread(url)
        self.thread.change_pixmap_signal.connect(self.process_frame)
        self.thread.stopped_signal.connect(self.on_video_stopped)
        self.thread.start()
        
        # Iniciar Workers de IA si no están corriendo
        if not self.detection_worker or not self.detection_worker.isRunning():
            self.start_ai_workers()

    @pyqtSlot()
    def stop_video(self):
        """Detiene el hilo de video si existe"""
        if self.thread:
            self.thread.stop()
        else:
            self.video_stopped_signal.emit()

    @pyqtSlot()
    def restart_video(self):
        """Reinicia la conexión de video"""
        if self.thread and self.thread.isRunning():
            url = self.thread.rtsp_url
            self.switch_camera(url)
            
    def on_video_stopped(self):
        """Callback cuando el hilo muere definitivamente"""
        self.thread = None
        self.video_stopped_signal.emit()
        self.log_signal.emit("Video desconectado correctamente.")

    def start_ai_workers(self):
        self.log_signal.emit("Iniciando IA...")
        
        # 1. Detection Worker
        self.detection_worker = DetectionWorker(model_path="yolo11m.pt") # Use YOLOv11m (Correct Name)
        # Conectar señal de detección -> Logic Worker
        self.detection_worker.detection_signal.connect(self.logic_worker.process_detections)
        # Conectar señal de detección -> UI (para dibujar cajitas)
        self.detection_worker.detection_signal.connect(self.detections_signal.emit)
        
        self.detection_worker.start()
        
        # 2. Logic Worker
        if not self.logic_worker.isRunning():
             self.logic_worker.start()

    def stop_ai_workers(self):
        if self.detection_worker:
            self.detection_worker.stop()
        # Logic worker puede seguir vivo o detenerse, mejor detenerlo
        # self.logic_worker.stop() 

    def start_monitoring(self):
        self.monitoring_active = True
        self.log_signal.emit("Sistema iniciado.")
        
        # Asegurar que Logic Worker esté vivo
        if not self.logic_worker.isRunning():
            self.logic_worker.start()

    def stop_monitoring(self):
        self.monitoring_active = False
        self.stop_video()
        self.stop_ai_workers()
        self.log_signal.emit("Sistema detenido.")

    @pyqtSlot(list)
    def update_roi(self, coords):
        """Recibe coordenadas del ROI desde la UI y las pasa al worker."""
        if self.detection_worker and self.detection_worker.is_running:
            self.detection_worker.set_roi(coords)
            # Activate Logic when ROI is set
            self.logic_worker.set_roi_active(True) 
            self.log_signal.emit(f"ROI actualizado: {len(coords)} puntos.")
        else:
            self.log_signal.emit("ROI guardado (IA no iniciada aún).")

    @pyqtSlot()
    def clear_roi(self):
        """Borra el ROI y desactiva la lógica asociada."""
        if self.detection_worker and self.detection_worker.is_running:
            self.detection_worker.set_roi([]) # Clear in Detection
        
        # Deactivate Logic (Resets counters)
        self.logic_worker.set_roi_active(False)
        self.log_signal.emit("ROI eliminado. Lógica desactivada.")
