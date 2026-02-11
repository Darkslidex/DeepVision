import sys
import time
import torch
import cv2
import numpy as np
from ultralytics import YOLO

def check_system():
    print("-" * 50)
    print("🔍 DIAGNÓSTICO DE HARDWARE DEEPVISION")
    print("-" * 50)

    # 1. VERIFICACIÓN DE CUDA (NVIDIA)
    print(f"Python Version: {sys.version.split()[0]}")
    try:
        cuda_available = torch.cuda.is_available()
        print(f"CUDA Disponible: {cuda_available}")
        
        if cuda_available:
            print(f"Dispositivo GPU: {torch.cuda.get_device_name(0)}")
            print(f"Versión CUDA: {torch.version.cuda}")
        else:
            print("⚠️ ADVERTENCIA: No se detecta NVIDIA CUDA.")
            print("   El sistema correrá en CPU (Muy lento).")
    except Exception as e:
        print(f"❌ Error verificando PyTorch: {e}")

    # 2. VERIFICACIÓN DE YOLO
    print("\n🧠 Cargando Cerebro (YOLO)...")
    try:
        model = YOLO('yolov8n.pt') 
        device = '0' if torch.cuda.is_available() else 'cpu'
        model.to(device)
        print(f"✅ Modelo cargado correctamente en: {model.device}")
        
        # Prueba real
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        model(dummy_frame, verbose=False) # Calentamiento
        
        start = time.time()
        model(dummy_frame, verbose=False)
        duration = (time.time() - start) * 1000
        print(f"⏱️ Tiempo de inferencia: {duration:.2f} ms")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    check_system()