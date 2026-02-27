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
        Signals the worker to stop. Waits up to 5 s; force-terminates if stuck.
        """
        self.logger.info(f"Stopping {self.name}...")
        self.is_running = False
        if not self.wait(5000):  # 5-second timeout
            self.logger.warning(f"{self.name} did not stop in time — forcing termination.")
            self.terminate()
            self.wait()
