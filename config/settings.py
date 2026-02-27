import os

class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        # Configuraciones por defecto
        self.app_name = "DeepVision SIAO"
        self.version = "1.0.0"
        self.db_path = "data/deepvision.db"
        self.log_level = "INFO"
        
        # Security
        self.db_password = os.getenv("DB_PASSWORD", "default_secure_password") 
        
        # Load from DB if available
        # We perform a local import to avoid circular dependency at module level
        try:
            from data.db import DBManager
            # Check if we can get an instance without triggering recursion
            # Since Settings is initializing, DBManager might be trying to get Settings.
            # We must be careful.
            # Ideally, Settings shouldn't depend on DBManager for basic paths.
            # But for runtime config (thresholds), we want DB.
            # We can use a property or lazy load?
            
            # Simple approach: Default values first
            self.yolo_model_path = "assets/models/yolov11.pt"
            self.rtsp_url = 0
            self.t1_continuous = 3.0
            self.t2_cumulative = 10.0
            self.t3_leak_rate = 2.0
            self.t_aforo = 5.0
            self.enable_aforo = True
            self.t_abandonment = 30.0 # Default 30s
            self.enable_abandonment = True
            self.max_people = 3 # Limite Aforo

            # Notification Settings (New)
            self.notification_direct_alert = False
            self.notification_warning_mode = True
            self.notification_warning_limit = 3
            self.notification_reduction_time = 60 # Minutes
            
            # Cell Phone Policy (New)
            self.cell_policy = "continuous" # strict, continuous, accumulated

            # Sensitivity
            self.chin_dist_threshold = 0.05 # Head drop threshold
            
            # Inactivity
            self.enable_inactivity = True
            self.inactivity_time_limit = 30.0 # Seconds
            self.inactivity_dist_threshold = 15 # Pixels

            # Fatigue Detection (New)
            self.enable_fatigue = False
            self.fatigue_policy = "warning" # 'warning' (lives) or 'critical' (immediate)

            # ROI (default empty — always initialized to avoid AttributeError)
            self.roi_coords = []
            
            # We'll skip loading from DB here to avoid the cycle during __init__.
            # We can load them later or just assume 'update' pushes to DB, 
            # and we need a 'sync' method?
            # Or better: DBManager calls Settings, Settings sets defaults.
            # Then Controller or Main loads settings from DB and updates Settings object?
            # Let's add a 'sync_from_db' method that Controller calls.
        except ImportError:
            pass

    def sync_from_db(self):
        """Loads values from DB, overriding defaults."""
        try:
            from data.db import DBManager
            db = DBManager()
            
            val = db.get_settings("t1_continuous")
            if val: self.t1_continuous = float(val)
            
            val = db.get_settings("t2_cumulative")
            if val: self.t2_cumulative = float(val)
            
            val = db.get_settings("t_aforo")
            if val: self.t_aforo = float(val)
            
            val = db.get_settings("enable_aforo")
            if val: self.enable_aforo = (val.lower() == 'true')

            val = db.get_settings("t_abandonment")
            if val: self.t_abandonment = float(val)

            val = db.get_settings("enable_abandonment")
            if val: self.enable_abandonment = (val.lower() == 'true')
            
            val = db.get_settings("max_people")
            if val: self.max_people = int(val)
            
            # Load Notification Settings
            val = db.get_settings("notification_direct_alert")
            if val: self.notification_direct_alert = (val.lower() == 'true')
            
            val = db.get_settings("notification_warning_mode")
            if val: self.notification_warning_mode = (val.lower() == 'true')

            val = db.get_settings("notification_warning_limit")
            if val: self.notification_warning_limit = int(val)

            val = db.get_settings("notification_reduction_time")
            if val: self.notification_reduction_time = int(val)
            
            val = db.get_settings("cell_policy")
            if val: self.cell_policy = val

            val = db.get_settings("chin_dist_threshold")
            if val: self.chin_dist_threshold = float(val)

            val = db.get_settings("enable_inactivity")
            if val: self.enable_inactivity = (val.lower() == 'true')

            val = db.get_settings("inactivity_time_limit")
            if val: self.inactivity_time_limit = float(val)

            val = db.get_settings("inactivity_dist_threshold")
            if val: self.inactivity_dist_threshold = int(val)

            
            val = db.get_settings("rtsp_url")
            if val: 
                # Try to cast to int if it's a digit (webcam index)
                if val.isdigit():
                    self.rtsp_url = int(val)
                else:
                    self.rtsp_url = val

            val = db.get_settings("roi_coords")
            if val:
                import ast
                try:
                    self.roi_coords = ast.literal_eval(val)
                except:
                    pass
                    
        except Exception as e:
            print(f"Failed to sync settings from DB: {e}")

    def update(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
            
            # Persist
            try:
                from data.db import DBManager
                db = DBManager()
                db.set_setting(key, str(value))
            except Exception as e:
                print(f"Failed to save setting {key}: {e}")
