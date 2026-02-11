from core.worker import BaseWorker
from core.logic.leaky_bucket import LeakyBucket
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import time

from config.settings import Settings

class LogicWorker(BaseWorker):
    """
    Procesa las detecciones para determinar si se disparan alarmas.
    Maneja la lógica de "Abandono de puesto" y uso de celular con políticas avanzadas.
    """
    alarm_signal = pyqtSignal(str, str, str) # Level, Type, Message
    bucket_status_signal = pyqtSignal(float, float) # Current, Capacity
    aforo_status_signal = pyqtSignal(int, int) # Current Count, Max Count
    cell_status_signal = pyqtSignal(float, float) # Current Time, Max Time
    warning_signal = pyqtSignal(str, str) # Type, Message (For Blocking Modal)
    
    def __init__(self):
        super().__init__(name="LogicWorker")
        self.settings = Settings()
        
        # Import inside to avoid circular deps if any, though logic->notification is fine
        from core.notification_service import NotificationService
        self.notifier = NotificationService()
        
        # Blocking State
        self.is_paused_for_warning = False
        
        # Abandonment
        self.abandonment_time_accumulated = 0.0
        self.last_process_time = time.time()
        self.last_abandonment_notification = 0.0
        
        # Cell Phone
        self.cell_time_continuous = 0.0  # For "Continuous" policy
        self.cell_try_loss_time = 0.0 # Time when cell phone was lost (for grace period)
        self.cell_time_accumulated_buffer = 0.0 # For "Accumulated" policy (T2)
        
        # Aforo
        self.aforo_violation_start = None
        
        # Warning System ("Good Conduct")
        self.current_warnings = 0
        self.last_warning_time = 0.0
        self.last_decay_check = time.time()
        
        # ROI State
        self.roi_active = False
        
    def set_roi_active(self, active: bool):
        self.roi_active = active
        if active:
            # CRITICAL: Reset time base to avoid "jump" (huge time_diff) from previous runs
            self.last_process_time = time.time()
        else:
            self.reset_counters()

    def reset_counters(self):
        """Resets all accumulation timers and clears UI status."""
        self.abandonment_time_accumulated = 0.0
        self.cell_time_continuous = 0.0
        self.cell_time_accumulated_buffer = 0.0
        self.cell_try_loss_time = 0.0
        self.current_warnings = 0 
        self.last_abandonment_notification = 0.0
        self.aforo_violation_start = None
        self.is_paused_for_warning = False # Ensure we unpause on reset
        
        # Emit cleared status to UI (Force update to 0)
        self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
        self.cell_status_signal.emit(0.0, 0.0)
        self.aforo_status_signal.emit(0, self.settings.max_people)
        
        # print("DEBUG: LogicWorker Counters Reset (No ROI)")


    def handle_alarm(self, level, type_str, message):
        """
        Central Incident Manager.
        Decides whether to notify the supervisor or just warn locally (Blocking).
        """
        current_time = time.time()
        
        # 0. CRITICAL OVERRIDE (Weapons)
        # If type is ARMA, ignore all warning logic and settings. FORCE NOTIFICATION.
        if type_str == "ARMA":
            self.notifier.send_alert("CRITICAL", type_str, message)
            self.alarm_signal.emit("CRITICAL", type_str, message)
            return

        # 1. Direct Alert? (Overrides everything)
        if getattr(self.settings, 'notification_direct_alert', False):
            self.notifier.send_alert(level, type_str, message)
            self.alarm_signal.emit(level, type_str, message)
            return

        # 2. Warning Mode Check (Strict)
        if not getattr(self.settings, 'notification_warning_mode', True):
            # Mode OFF: Just emit standard alarm (non-blocking)
            self.alarm_signal.emit(level, type_str, message)
            return

        # 3. Warning Logic (Blocking System)
        self.current_warnings += 1
        self.last_warning_time = current_time
        
        warning_limit = getattr(self.settings, 'notification_warning_limit', 3)
        
        if self.current_warnings < warning_limit:
            # CASE A: Has Lives -> BLOCKING WARNING (Pause & Modal)
            self.is_paused_for_warning = True
            
            # Emit signal to UI to show Modal
            # Logic: "Advertencia X de Limit"
            full_msg = f"{message}\n\nAdvertencia {self.current_warnings} de {warning_limit}."
            self.warning_signal.emit(type_str, full_msg)
            
            # We do NOT emit alarm_signal here to avoid double audio/logging if the modal handles it?
            # Or we emit it as WARNING level? Let's emit for log purposes.
            self.alarm_signal.emit("WARNING", type_str, full_msg)
            return
            
        else:
            # CASE B: No Lives -> CRITICAL ESCALATION (Non-blocking, Notification)
            full_msg = f"{message} (Escalado por {self.current_warnings} advertencias)"
            
            self.notifier.send_alert("CRITICAL", type_str, full_msg)
            self.alarm_signal.emit("CRITICAL", "ESCALADO", full_msg)
            # We do NOT pause here. System continues monitoring (and likely escalating again if not fixed).

    @pyqtSlot(str)
    def resume_from_warning(self, warning_type):
        """
        Called by UI when user accepts the warning.
        Resets the specific counter and unpauses.
        """
        print(f"DEBUG: Resuming from warning: {warning_type}")
        self.is_paused_for_warning = False
        
        # Reset the specific timer that caused the issue to give them a chance
        if warning_type == "CELULAR":
            self.cell_time_continuous = 0.0
            self.cell_time_accumulated_buffer = 0.0
            self.cell_try_loss_time = 0.0
            self.cell_status_signal.emit(0.0, 0.0)
            self.last_cell_alert = time.time() # Prevent immediate re-trigger
            
        elif warning_type == "ABANDONO":
            self.abandonment_time_accumulated = 0.0
            self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
            self.last_abandonment_notification = time.time()
            
        elif warning_type == "AFORO":
            self.aforo_violation_start = None
            self.last_aforo_alert = time.time()

    def check_good_conduct(self):
        """
        Reduces warning count if enough time passed without incidents.
        """
        if self.current_warnings == 0:
            return

        current_time = time.time()
        # Check every 10 seconds to avoid spamming checks
        if (current_time - self.last_decay_check) < 10.0:
            return
            
        self.last_decay_check = current_time
        
        reduction_minutes = getattr(self.settings, 'notification_reduction_time', 60)
        reduction_seconds = reduction_minutes * 60
        
        # Time since last warning
        if (current_time - self.last_warning_time) > reduction_seconds:
            self.current_warnings -= 1
            self.last_warning_time = current_time # Reset timer for next reduction
            # print(f"[GOOD CONDUCT] One warning removed. Remaining: {self.current_warnings}")
            # Optional: Emit a positive signal/toast? 
 

    @pyqtSlot(object)
    def process_detections(self, detections):
        if not self.is_running:
            return

        # BLOCKING WARNING CHECK
        if self.is_paused_for_warning:
            # User requested "Passthrough Logic": 
            # Logic pauses (no counters, no alarms), but Video continues (handled by Controller/VideoThread).
            # So we just return here effectively freezing the logic state.
            return

        # NEW: Check if ROI is active
        if not self.roi_active:
            # FORCE RESET to prevent "Ghost Counters"
            self.reset_counters()
            return

        current_time = time.time()
        time_diff = current_time - self.last_process_time
        self.last_process_time = current_time
        
        self.check_good_conduct()
        
        # --- 1. Aforo Check ---
        total_people = sum(1 for d in detections if d['class'] == 'person')
        # Display Status
        self.aforo_status_signal.emit(total_people, self.settings.max_people)
        
        # Check Limit
        if self.settings.enable_aforo and total_people > self.settings.max_people:
             if self.aforo_violation_start is None:
                 self.aforo_violation_start = current_time
             elif (current_time - self.aforo_violation_start) > self.settings.t_aforo:
                 # Check debounce for alert
                 if (current_time - getattr(self, 'last_aforo_alert', 0)) > 5.0:
                     self.handle_alarm("ALARM", "AFORO", f"Exceso de personas: {total_people} > {self.settings.max_people}")
                     self.last_aforo_alert = current_time
        else:
             self.aforo_violation_start = None

        # --- 2. Cell Phone Check (New Policies) ---
        cell_detected = False
        max_conf = 0.0
        for d in detections:
            if d['class'] == 'cell phone' and d.get('in_roi', False):
                # User requested 0.3 sensitivity
                if d['conf'] > 0.3:
                    cell_detected = True
                    max_conf = max(max_conf, d['conf'])
                    # Debug print REMOVED for performance
                    # print(f"DEBUG: Cell detected in ROI. Conf: {d['conf']:.2f}")

        policy = getattr(self.settings, 'cell_policy', 'continuous')
        
        # POLICY: STRICT
        if self.settings.cell_policy == 'strict':
             # T0 Strict: 0 tolerance
             if self.cell_time_continuous > 0.1:
                 # Check debounce
                 if (current_time - getattr(self, 'last_cell_alert', 0)) > 5.0:
                     self.handle_alarm("ALARM", "CELULAR", f"Uso de celular detectado ({self.cell_time_continuous:.1f}s)")
                     self.last_cell_alert = current_time
        
        # --- 3. Weapon Detection (Immediate) ---
        # Class 43 = knife, Class 76 = scissors
        weapons = [d for d in detections if d['class'] in ['knife', 'scissors']]
        if weapons:
            # Debounce slightly just to avoid spamming the signal in 1 millisecond
            if (current_time - getattr(self, 'last_weapon_alert', 0)) > 3.0:
                self.handle_alarm("CRITICAL", "ARMA", "OBJETO PELIGROSO DETECTADO")
                self.last_weapon_alert = current_time
            self.cell_status_signal.emit(0.0, 0.0) # Not relevant for key
        
        # --- 4. Fatigue Detection (Chin-to-Chest) ---
        if getattr(self.settings, 'enable_fatigue', False):
            # Check for fatigue stats in detections (Persons only)
            persons_with_pose = [d for d in detections if d['class'] == 'person' and d.get('fatigue') and d['fatigue'].get('has_pose')]
            
            sleep_detected = False
            
            for p in persons_with_pose:
                data = p['fatigue']
                chin_dist = data.get('chin_dist', 999.0)
                
                # Heuristic: Chin-to-Chest
                # If chin_dist is small (or negative depending on coord system), head is down.
                # Threshold from settings (e.g., 0.05)
                # If chin_dist < threshold -> HEAD DOWN
                if chin_dist < self.settings.chin_dist_threshold:
                    sleep_detected = True
            
            # --- Timers ---
            dt = 0.1 # Approx
            
            # Sleep Timer
            if sleep_detected:
                self.sleep_time = getattr(self, 'sleep_time', 0.0) + dt
            else:
                self.sleep_time = max(0.0, getattr(self, 'sleep_time', 0.0) - dt*2)
                
            # --- Trigger ---
            policy = getattr(self.settings, 'fatigue_policy', 'warning')
            
            # Trigger (5 seconds as requested)
            if self.sleep_time > 5.0:
                if (current_time - getattr(self, 'last_fatigue_alert', 0)) > 5.0:
                     msg = "SUEÑO DETECTADO (Cabeceo)"
                     if policy == 'critical':
                         self.handle_alarm("CRITICAL", "SUEÑO", msg)
                     else:
                         self.handle_alarm("WARNING", "SUEÑO", msg)
                     self.last_fatigue_alert = current_time
                     self.sleep_time = 0

        # --- 5. Inactivity Detection (New) ---
        if getattr(self.settings, 'enable_inactivity', False):
            # Find primary person (largest confidence or area?)
            # Let's use the first person in ROI with pose
            person = next((d for d in detections if d['class'] == 'person' and d.get('in_roi', False) and d.get('fatigue')), None)
            
            if person:
                centroid = person['fatigue'].get('centroid') # (cx, cy) normalized
                
                if centroid:
                    # Convert to Pixels for distance check (assuming 1920x1080 ref or just use normalized diff?)
                    # Settings threshold is pixels (15px). Let's assume standardized 640x480 or similar for logic?
                    # Or just convert back using an arbitrary reference W/H?
                    # Let's iterate: The previous logic didn't have W/H. 
                    # We can store last_centroid as Normalized.
                    # threshold_norm = 15 / 1000 = 0.015 approx.
                    
                    last_c = getattr(self, 'last_inactivity_centroid', None)
                    last_move_t = getattr(self, 'last_movement_time', current_time)
                    
                    if last_c:
                        # Euclidean Distance (Normalized)
                        import math
                        dx = centroid[0] - last_c[0]
                        dy = centroid[1] - last_c[1]
                        dist_norm = math.sqrt(dx*dx + dy*dy)
                        
                        # Rough conversion to pixels (assuming 1080p for high sens, or 640p?)
                        # 15px on 1080p is ~0.014. 
                        # 15px on 480p is ~0.03.
                        # User said "15 pixeles". Let's assume 1080p (standard CCTV).
                        dist_px = dist_norm * 1080.0 
                        
                        if dist_px > self.settings.inactivity_dist_threshold:
                            # MOVED: Reset timer
                            self.last_movement_time = current_time
                            # Update last known position
                            self.last_inactivity_centroid = centroid
                        else:
                            # STATIC: Check Timer
                            time_static = current_time - last_move_t
                            if time_static > self.settings.inactivity_time_limit:
                                if (current_time - getattr(self, 'last_inactivity_alert', 0)) > 5.0:
                                    self.handle_alarm("WARNING", "INACTIVIDAD", f"Operador inmóvil por {int(time_static)}s")
                                    self.last_inactivity_alert = current_time
                    else:
                        # First init
                        self.last_inactivity_centroid = centroid
                        self.last_movement_time = current_time
            else:
                # No person? Reset or Pause?
                # If no person, maybe Abandonment handles it. 
                # Reset Inactivity timer.
                self.last_movement_time = current_time
                self.last_inactivity_centroid = None

        # POLICY: CONTINUOUS (T1) -> Keep existing logic below...
        # ... (Rest of file is Cell Phone / Abandonment)

        # POLICY: CONTINUOUS (T1)
        elif policy == 'continuous':
            limit = getattr(self.settings, 't1_continuous', 3.0)
            
            if cell_detected:
                # Cell IS detected:
                # 1. Reset loss timer (we found it!)
                self.cell_try_loss_time = 0.0
                # 2. Increment continuous timer
                self.cell_time_continuous += time_diff
            else:
                # Cell NOT detected:
                if self.cell_time_continuous > 0.0:
                    # We had a timer running. Check Grace Period.
                    if self.cell_try_loss_time == 0.0:
                        # First frame of loss: Start timer
                        self.cell_try_loss_time = current_time
                    
                    time_lost = current_time - self.cell_try_loss_time
                    if time_lost < 2.0:
                        # GRACE PERIOD: Hold timer (Pause)
                        pass 
                    else:
                        # TIMEOUT: Reset
                        self.cell_time_continuous = 0.0
                        self.cell_try_loss_time = 0.0
                else:
                    # Timer was 0, so just keep it 0
                    self.cell_try_loss_time = 0.0

            self.cell_status_signal.emit(self.cell_time_continuous, limit)
            
            if self.cell_time_continuous > limit:
                if (current_time - getattr(self, 'last_cell_alert', 0)) > 2.0:
                    self.handle_alarm("ALARM", "CELULAR", f"Uso continuo durante {limit}s")
                    self.last_cell_alert = current_time
                    # Reset after alert? Or keep alerting?
                    # Let's reset to allow re-trigger or keep high?
                    # User said "Uniforme y estático". If we reset, it disappears.
                    # Let's keep it until loss > 2s. Can clutter notifications though.
                    # Logic: If > limit, we alerted. We can clamp it or let it grow?
                    # Let's let it grow for UI visual, but limit alerts.
                    pass
        
        # POLICY: ACCUMULATED (T2)
        elif policy == 'accumulated':
            limit = getattr(self.settings, 't2_cumulative', 10.0)
            if cell_detected:
                self.cell_time_accumulated_buffer += time_diff
            else:
                # Slow decay? Or no decay? Typical Leaky Bucket.
                # Let's use T3 Leak Rate
                leak_rate = getattr(self.settings, 't3_leak_rate', 1.0) # units/sec?
                # Actually settings has T3? Yes.
                # Decay
                self.cell_time_accumulated_buffer = max(0.0, self.cell_time_accumulated_buffer - (leak_rate * time_diff))
            
            self.cell_status_signal.emit(self.cell_time_accumulated_buffer, limit)
            
            if self.cell_time_accumulated_buffer > limit:
                 if (current_time - getattr(self, 'last_cell_alert', 0)) > 5.0:
                     self.handle_alarm("ALARM", "CELULAR", f"Uso acumulado > {limit}s")
                     self.last_cell_alert = current_time
                     self.cell_time_accumulated_buffer = limit - 2.0 # Dropping slightly to avoid rapid re-trigger

        # --- 3. Abandonment Check ---
        if not self.settings.enable_abandonment:
            self.bucket_status_signal.emit(0.0, self.settings.t_abandonment)
        else:
            person_in_roi = any(d['class'] == 'person' and d.get('in_roi', False) for d in detections)
            
            if person_in_roi:
                self.abandonment_time_accumulated = 0.0
            else:
                self.abandonment_time_accumulated += time_diff
            
            self.bucket_status_signal.emit(self.abandonment_time_accumulated, self.settings.t_abandonment)

            if self.abandonment_time_accumulated >= self.settings.t_abandonment:
                if (current_time - self.last_abandonment_notification) > 5.0:
                    self.handle_alarm("CRITICAL", "ABANDONO", f"Abandono detectado ({self.abandonment_time_accumulated:.1f}s)")
                    self.last_abandonment_notification = current_time
            else:
                self.last_abandonment_notification = 0.0

    def work(self):
        while self.is_running:
            time.sleep(1)

