import subprocess
import sys

def run_command(command):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def fix_dependencies():
    print("--- STARTING DEPENDENCY REPAIR (Protobuf Downgrade) ---")
    
    python_exe = sys.executable
    
    # 1. Uninstall
    print("\n[ACTION] Uninstalling mediapipe and protobuf...")
    subprocess.call(f'"{python_exe}" -m pip uninstall mediapipe protobuf -y', shell=True)
    
    # 2. Install Pinned Versions
    print("\n[ACTION] Installing protobuf<4 and mediapipe...")
    # Using --no-cache-dir to ensure clean install
    # Quoting "protobuf<4" is important for shell
    cmd = f'"{python_exe}" -m pip install "protobuf<4" mediapipe --no-cache-dir'
    
    if run_command(cmd):
        print("✅ [SUCCESS] Installation command completed.")
    else:
        print("❌ [ERROR] Installation failed.")
        return

    # 3. Verification
    print("\n--- VERIFICATION ---")
    print("Testing import...")
    try:
        # Check specific import
        verify_cmd = f'"{python_exe}" -c "import mediapipe as mp; print(\'MediaPipe Version:\', mp.__version__); import mediapipe.solutions; print(\'✅ ÉXITO: MediaPipe solutions cargado.\'); import google.protobuf; print(\'Protobuf Version:\', google.protobuf.__version__)"'
        subprocess.check_call(verify_cmd, shell=True)
        
        print("\n✅✅✅ REPARACIÓN EXITOSA. AHORA PUEDES EJECUTAR MAIN.PY ✅✅✅")
            
    except subprocess.CalledProcessError:
        print(f"\n❌ REPARACIÓN FALLIDA. El import sigue fallando.")
    except Exception as e:
        print(f"\n❌ REPARACIÓN FALLIDA. Error inesperado: {e}")

if __name__ == "__main__":
    fix_dependencies()
