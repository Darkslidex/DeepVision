import sys
import os
import time
import traceback
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCKING SETUP START ---
# We need to define pyqtSlot as a pass-through decorator before importing PyQt6
def pyqtSlot(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# Mock modules
mock_qt_core = MagicMock()
mock_qt_core.pyqtSlot = pyqtSlot
mock_qt_core.pyqtSignal = MagicMock()

class MockQObject:
    def __init__(self, *args, **kwargs):
        pass

class MockQThread(MockQObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def start(self): pass
    def stop(self): pass
    def wait(self): pass

mock_qt_core.QObject = MockQObject
mock_qt_core.QThread = MockQThread

sys.modules["PyQt6.QtCore"] = mock_qt_core
sys.modules["PyQt6.QtWidgets"] = MagicMock()
sys.modules["PyQt6.QtGui"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["ultralytics"] = MagicMock()
sys.modules["mediapipe"] = MagicMock()

# Mock DBManager and WhatsAppService imports
mock_db = MagicMock()
mock_db.DBManager = MagicMock
sys.modules["data.db"] = mock_db

mock_wa = MagicMock()
mock_wa.WhatsAppService = MagicMock
sys.modules["services.whatsapp"] = mock_wa

# --- MOCKING SETUP END ---

# Import Dependencies
from config.settings import Settings
# Mock logging before importing controller
import logging
logging.getLogger = MagicMock()

try:
    from core.controller import SystemController
except ImportError:
    print("Failed to import SystemController")
    traceback.print_exc()
    sys.exit(1)

def test_logic():
    with open("tests/results.txt", "w") as f:
        f.write("--- Starting Logic Verification ---\n")
        try:
            # 1. Setup
            if Settings._instance:
                Settings._instance = None
            
            # Reset mocks
            mock_db.DBManager.return_value = MagicMock()
            mock_wa.WhatsAppService.return_value = MagicMock()
            
            settings = Settings()
            settings.roi_coords = [(0, 0, 100, 100)] 
            settings.t_aforo = 1.0 
            settings.t1_continuous = 3.0
            
            # Instantiate Controller
            controller = SystemController()
            # Ensure controller logger is mock
            controller.logger = MagicMock()
            
            # Ensure worker loggers are mocks
            if hasattr(controller, 'detection_worker'):
                controller.detection_worker.logger = MagicMock()
                # Detection worker might need is_running
                controller.detection_worker.is_running = True
            
            controller.settings = settings
            controller.db_manager = MagicMock()
            controller.whatsapp_service = MagicMock()
            controller.leaky_bucket = MagicMock()
            controller.leaky_bucket.update.return_value = False
            
            # Capture triggered alarms
            alarms = []
            def capture_alarm(level, type, msg):
                alarms.append((level, type))
            
            controller.trigger_alarm = capture_alarm
            
            # 2. Test Scenarios
            
            # Scenario A: Normal Operation (1 Person in ROI)
            alarms.clear()
            detections_normal = [{'class': 'person', 'in_roi': True}]
            controller.handle_detections(detections_normal)
            time.sleep(0.1)
            if not alarms:
                f.write("PASS: Scenario A (Normal Operation)\n")
            else:
                f.write(f"FAIL: Scenario A (Alarms triggered: {alarms})\n")

            # Scenario B: Abandonment (0 People)
            alarms.clear()
            detections_empty = []
            
            # First tick - should start timer and NOT trigger alarm
            controller.handle_detections(detections_empty)
            if alarms:
                 f.write(f"FAIL: Scenario B (Alarm triggered prematurely: {alarms})\n")
                 alarms.clear()
            
            # Wait 3.1s (Debounce is 3.0s)
            time.sleep(3.1) 
            controller.handle_detections(detections_empty)
            
            found_abandon = any(t == "ABANDONMENT" for l, t in alarms)
            if found_abandon:
                 f.write("PASS: Scenario B (Abandonment)\n")
            else:
                 f.write("FAIL: Scenario B (Abandonment alarm NOT triggered)\n")

            # Scenario C: Overcrowding (1 in ROI + 1 Outside)
            alarms.clear()
            # Reset abandonment by sending normal frame
            controller.handle_detections(detections_normal) 
            alarms.clear() # Clear any abandonment clearance or noise
            
            detections_overcrowd = [
                {'class': 'person', 'in_roi': True},
                {'class': 'person', 'in_roi': False}
            ]
            
            # First tick
            controller.handle_detections(detections_overcrowd)
            
            # Wait 1.1s (t_aforo is 1.0s)
            time.sleep(1.1)
            controller.handle_detections(detections_overcrowd)
            
            found_aforo = any(t == "OVERCROWDING" for l, t in alarms)
            if found_aforo:
                 f.write("PASS: Scenario C (Overcrowding)\n")
            else:
                 f.write("FAIL: Scenario C (Overcrowding alarm NOT triggered)\n")

            # Scenario D: Phone in ROI
            alarms.clear()
            # Mock settings T1
            controller.settings.t1_continuous = 0.5 
            
            detections_phone_roi = [
                {'class': 'person', 'in_roi': True},
                {'class': 'cell phone', 'in_roi': True}
            ]
            
            # First tick - starts timer
            controller.handle_detections(detections_phone_roi)
            
            # Wait
            time.sleep(0.6)
            
            # Second tick - triggers alarm
            controller.handle_detections(detections_phone_roi)
            
            found_phone = any(t == "CELLPHONE_CONTINUOUS" for l, t in alarms)
            if found_phone:
                 f.write("PASS: Scenario D (Phone inside ROI)\n")
            else:
                 f.write("FAIL: Scenario D (Phone alarm NOT triggered)\n")

            # Scenario E: Phone Outside ROI (Should NOT trigger)
            alarms.clear()
            # Clear previous state
            controller.continuous_start_time = None
            
            detections_phone_out = [
                {'class': 'person', 'in_roi': True}, # Operator present
                {'class': 'cell phone', 'in_roi': False} # Phone elsewhere
            ]
            
            controller.handle_detections(detections_phone_out)
            time.sleep(0.6)
            controller.handle_detections(detections_phone_out)
            
            if not alarms:
                 f.write("PASS: Scenario E (Phone outside ROI)\n")
            else:
                 f.write(f"FAIL: Scenario E (Alarm triggered: {alarms})\n")
                 
        except Exception:
            f.write("FAIL: Exception occurred\n")
            f.write(traceback.format_exc())
            print("Exception in test_logic:")
            traceback.print_exc()

if __name__ == "__main__":
    test_logic()
