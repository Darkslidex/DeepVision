from PyQt6.QtCore import QThread, pyqtSignal, QObject
import time
import logging

class WorkerCanceledException(Exception):
    pass

class BaseWorker(QThread):
    """
    Base class for all background workers (IA, DB, Logic).
    Handles thread lifecycle, error reporting, and safe stopping.
    """
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, name="Worker"):
        super().__init__()
        self.name = name
        self.is_running = True
        self.logger = logging.getLogger(f"DeepVision.{name}")

    def run(self):
        print("🚀 [DEBUG] EL WORKER HA ARRANCADO. INICIANDO BUCLE...")
        self.logger.info(f"Starting {self.name} thread...")
        try:
            self.work()
        except WorkerCanceledException:
            self.logger.info(f"{self.name} stopped safely.")
        except Exception as e:
            self.logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)
            self.error_signal.emit(str(e))
        finally:
            self.is_running = False
            self.finished_signal.emit()

    def work(self):
        """
        Override this method with the actual heavy lifting.
        Must check self.is_running periodically.
        """
        raise NotImplementedError("Workers must implement the work method")

    def stop(self):
        """
        Signals the worker to stop.
        """
        self.logger.info(f"Stopping {self.name}...")
        self.is_running = False
        self.wait()
