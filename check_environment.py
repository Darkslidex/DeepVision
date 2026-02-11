import sys
import os
import platform
import subprocess

def print_status(component, status, message):
    if status:
        # Green check
        print(f"\033[92m[PASS] {component}: {message}\033[0m")
    else:
        # Red cross
        print(f"\033[91m[FAIL] {component}: {message}\033[0m")

print("\n==========================================")
print("   DIAGNÓSTICO DE SISTEMA DEEPVISION")
print("==========================================\n")

# 1. Python Check
print_status("Python", True, f"{sys.version.split()[0]} running from {sys.executable}")

# 2. PyTorch & CUDA Check
torch_ok = False
try:
    import torch
    print_status("PyTorch Import", True, f"Version {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        cuda_version = torch.version.cuda
        device_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0)
        print_status("CUDA Availability", True, f"YES (Version {cuda_version})")
        print_status("GPU Check", True, f"Detected {device_count} device(s): {device_name}")
        
        # Tensor Test
        try:
            x = torch.rand(5, 3).cuda()
            print_status("Tensor Operation", True, "Successfully created tensor on GPU")
            torch_ok = True
        except Exception as e:
            print_status("Tensor Operation", False, f"Failed to allocate on GPU: {e}")
    else:
        print_status("CUDA Availability", False, "NO - Configured for CPU only!")
        print_status("GPU Check", False, "N/A")

except ImportError as e:
    print_status("PyTorch Import", False, f"Not installed or DLL error: {e}")
except Exception as e:
    print_status("PyTorch Check", False, f"Unexpected error: {e}")

# 3. Ultralytics Check
try:
    import ultralytics
    from ultralytics import YOLO
    print_status("Ultralytics", True, f"Version {ultralytics.__version__}")
    
    # Check if we can load a model (optional, ensures library integrity)
    # try:
    #     model = YOLO("yolov8n.pt")
    #     print_status("YOLO Model Load", True, "Successfully loaded yolov8n.pt")
    # except Exception as e:
    #     print_status("YOLO Model Load", False, f"Failed to load model: {e}")

except ImportError:
    print_status("Ultralytics", False, "Module not found")
except Exception as e:
    print_status("Ultralytics", False, f"Error: {e}")

# 4. OpenCV Check
try:
    import cv2
    print_status("OpenCV", True, f"Version {cv2.__version__}")
except ImportError:
    print_status("OpenCV", False, "Module not found")

# 5. PyQt6 Check
try:
    from PyQt6.QtCore import QT_VERSION_STR
    print_status("PyQt6", True, f"Version {QT_VERSION_STR}")
except ImportError:
    print_status("PyQt6", False, "Module not found")
except Exception as e:
    print_status("PyQt6", False, f"Error: {e}")


print("\n------------------------------------------")
if torch_ok:
    print("\033[92m>>> RESULTADO FINAL: ENTORNO CONFIGURADO CORRECTAMENTE PARA GPU <<<\033[0m")
    print("Para iniciar el sistema usa: .\\.venv\\Scripts\\python main.py")
else:
    print("\033[91m>>> RESULTADO FINAL: ERRORES DETECTADOS. REVISE LOS LOGS. <<<\033[0m")
print("------------------------------------------\n")
