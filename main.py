import sys
import logging
import traceback
from PyQt6.QtWidgets import QApplication
from config.settings import Settings
from ui.main_window import MainWindow
from core.controller import SystemController

# --- Global Exception Handler ---
def global_exception_handler(exctype, value, tb):
    """
    Captures unhandled exceptions and logs them to file and console.
    """
    logger = logging.getLogger("DeepVision.Global")
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Uncaught Exception:\n{error_msg}")
    sys.__excepthook__(exctype, value, tb) # Call default handler

sys.excepthook = global_exception_handler

def main():
    # Inicializar configuración
    settings = Settings()
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("DeepVision")
    logger.info("Iniciando DeepVision...")

    app = QApplication(sys.argv)
    
    # Aplicar tema oscuro
    app.setStyle("Fusion")
    
    # Setup System
    controller = SystemController()
    window = MainWindow()
    
    # --- Integration UI <-> Controller ---
    
    # 1. Video Stream
    controller.frame_signal.connect(window.update_frame)
    
    # 2. Detections (Visual Overlay)
    controller.detections_signal.connect(window.update_detections)
    
    # 3. Logs & Alarms
    controller.log_signal.connect(lambda msg: window.log_event("SISTEMA", msg))
    controller.alarm_signal.connect(window.handle_alarm)
    controller.bucket_status_signal.connect(window.update_bucket_status)

    # 4. ROI Changes from UI to Controller
    def on_roi_drawn(coords):
        logger.info(f"ROI Updated (Mapped): {coords}")
        settings.update("roi_coords", coords) # Persist ROI
        # Send to Controller -> DetectionWorker
        controller.update_roi(coords)

    # Connect to the MAPPED signal from MainWindow, not the raw one from Overlay
    window.roi_updated.connect(on_roi_drawn)
    
    # NEW: Blocking Warning Signals
    controller.logic_worker.warning_signal.connect(window.show_blocking_warning)
    window.warning_accepted_signal.connect(controller.logic_worker.resume_from_warning)
    
    # 5. Config Changes (Restart Video)
    window.request_restart_video.connect(controller.restart_video)
    
    # 6. Camera Switching (Sidebar)
    window.request_switch_camera.connect(controller.switch_camera)
    
    # 7. Disconnect Video
    window.request_stop_video.connect(controller.stop_video)
    
    # 8. Video Stopped/Disconnected (Reset UI to show black screen)
    controller.video_stopped_signal.connect(window.reset_video_ui)
    
    # 9. Clear ROI
    window.clear_roi_signal.connect(controller.clear_roi)
    window.clear_roi_signal.connect(lambda: settings.update("roi_coords", []))

    
    # Show Window
    window.show()
    
    # Start Backend
    controller.start_monitoring()
    
    ret = app.exec()
    controller.stop_monitoring()
    sys.exit(ret)

if __name__ == "__main__":
    main()
