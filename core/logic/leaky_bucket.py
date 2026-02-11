import time

class LeakyBucket:
    def __init__(self, capacity=10.0, leak_rate=2.0):
        """
        :param capacity: Total seconds allowed (T_acumulado) before alarm.
        :param leak_rate: Seconds to subtract per second of non-usage (k).
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.current_level = 0.0
        self.last_update_time = time.time()
        self.alarm_triggered = False

    def update(self, is_using_phone):
        """
        Updates the bucket level based on current usage.
        Returns True if alarm should be triggered.
        """
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        if is_using_phone:
            # Add time to bucket (1s per 1s real time)
            self.current_level += dt
        else:
            # Leak from bucket
            self.current_level -= dt * self.leak_rate

        # Clamp level
        self.current_level = max(0.0, self.current_level)
        
        # Check alarm
        if self.current_level >= self.capacity:
            self.current_level = self.capacity # Cap at max
            if not self.alarm_triggered:
                self.alarm_triggered = True
                return True
        else:
            # Reset alarm trigger if level drops significantly (hysteresis could be added here)
            if self.current_level < self.capacity * 0.8:
                self.alarm_triggered = False
        
        return False

    def reset(self):
        self.current_level = 0.0
        self.alarm_triggered = False
