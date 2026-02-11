import os
import subprocess
import sys
import shutil

def run_command(command):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def fix_environment():
    print("--- STARTING ENVIRONMENT REPAIR ---")
    
    # 1. Detect Conflicts
    cwd = os.getcwd()
    potential_conflicts = ['mediapipe.py', 'mediapipe']
    
    conflict_found = False
    for item in potential_conflicts:
        path = os.path.join(cwd, item)
        if os.path.exists(path):
            conflict_found = True
            new_name = f"{item}_backup_conflict"
            new_path = os.path.join(cwd, new_name)
            print(f"⚠️ [CONFLICT FOUND] '{item}' found in {cwd}.")
            try:
                os.rename(path, new_path)
                print(f"✅ [ACTION] Renamed to '{new_name}'")
            except Exception as e:
                print(f"❌ [ERROR] Could not rename {item}: {e}")
    
    if not conflict_found:
        print("ℹ️ No local naming conflicts found (good).")

    # 2. Reinstall
    print("\n--- REINSTALLING LIBRARIES ---")
    python_exe = sys.executable
    
    print("[ACTION] Uninstalling mediapipe...")
    # Ignoring errors on uninstall in case it's not installed
    subprocess.call(f'"{python_exe}" -m pip uninstall mediapipe -y', shell=True)
    
    print("[ACTION] Installing mediapipe (no cache)...")
    # Using --force-reinstall to be sure
    if run_command(f'"{python_exe}" -m pip install mediapipe --no-cache-dir --force-reinstall'):
        print("✅ [SUCCESS] Installation command completed.")
    else:
        print("❌ [ERROR] Installation failed.")
        return

    # 3. Verification
    print("\n--- VERIFICATION ---")
    print("Testing import...")
    try:
        # Force reload possibilities by running in a subprocess verification to be 100% sure of the environment state
        verify_cmd = f'"{python_exe}" -c "import mediapipe; print(\'MediaPipe Location:\', mediapipe.__file__); import mediapipe.solutions; print(\'Solutions found!\')"'
        subprocess.check_call(verify_cmd, shell=True)
        
        print("\n✅✅✅ REPARACIÓN EXITOSA. AHORA PUEDES EJECUTAR MAIN.PY ✅✅✅")
            
    except subprocess.CalledProcessError:
        print(f"\n❌ REPARACIÓN FALLIDA. El import sigue fallando.")
    except Exception as e:
        print(f"\n❌ REPARACIÓN FALLIDA. Error inesperado: {e}")

if __name__ == "__main__":
    fix_environment()
