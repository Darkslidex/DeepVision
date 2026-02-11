import subprocess
import time
import sys
import os

WATCH_CMD = [sys.executable, "main.py"]
RESTART_DELAY = 5  # Seconds to wait before restarting

def start_process():
    print(f"[Watchdog] Starting DeepVision: {' '.join(WATCH_CMD)}")
    return subprocess.Popen(WATCH_CMD, cwd=os.getcwd())

def main():
    process = start_process()
    
    while True:
        try:
            # Check if process is still running
            ret_code = process.poll()
            
            if ret_code is not None:
                print(f"[Watchdog] Process ended with code {ret_code}.")
                
                # If code is 0, it was a clean exit requested by user
                if ret_code == 0:
                    print("[Watchdog] Clean exit. Stopping watchdog.")
                    break
                
                # Otherwise, restart
                print(f"[Watchdog] Unexpected exit. Restarting in {RESTART_DELAY} seconds...")
                time.sleep(RESTART_DELAY)
                process = start_process()
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("[Watchdog] Watchdog stopped by user.")
            if process.poll() is None:
                process.terminate()
            break
        except Exception as e:
            print(f"[Watchdog] Error: {e}")
            break

if __name__ == "__main__":
    # Ensure we are in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    main()
