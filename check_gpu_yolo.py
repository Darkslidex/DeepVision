import sys
import time

try:
    import torch
    import cv2
    import numpy as np
    from ultralytics import YOLO
except ImportError as e:
    print("-" * 40)
    print("ERROR FATAL DE DEPENDENCIAS")
    print(f"No se pudo importar una libreria necesaria: {e}")
    print("Probablemente te falta instalar: pip install torch torchvision ultralytics opencv-python")
    print("-" * 40)
    sys.exit(1)

def check_gpu_yolo():
    print("-" * 40)
    print("INICIO DIAGNOSTICO DE HARDWARE Y IA")
    print("-" * 40)

    # 1. Verificar CUDA
    print("\n[1] Verificando Aceleracion por GPU (CUDA)...")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"Tarjeta Grafica detectada: {torch.cuda.get_device_name(0)}")
        device = 'cuda'
    else:
        print("ADVERTENCIA: No se detecto GPU NVIDIA. Se usara CPU (esto sera lento).")
        device = 'cpu'

    # 2. Verificar Modelo
    print("\n[2] Verificando Carga del Modelo...")

    # Intentamos cargar 'yolov8n.pt' como pidio el usuario, pero tambien el proyecto usa 'yolov11n.pt'
    # Intentare yolov8n.pt primero
    model_name = 'yolov8n.pt'
    
    try:
        print(f"Intentando cargar '{model_name}'...")
        model = YOLO(model_name)
        model.to(device)
        print("Modelo cargado EXITOSAMENTE.")
    except Exception as e:
        print(f"Error loading model: {e}")
        # Si falla, intentar yolov11n.pt por si acaso es el que tienen
        try:
            print("Intentando alternativo 'yolov11n.pt'...")
            model = YOLO('yolov11n.pt')
            model.to(device)
            print("Modelo 'yolov11n.pt' cargado EXITOSAMENTE.")
        except:
             print("No se pudo cargar ningun modelo. Revisa tu internet o los archivos .pt.")
             return

    # 3. Prueba de Inferencia
    print("\n[3] Prueba de Inferencia (Velocidad)...")
    # Generar imagen vacia (negra) 640x640
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    
    # Calentamiento (primera inferencia suele ser lenta)
    print("Ejecutando warm-up...")
    model(img, verbose=False) 
    
    # Medir tiempo real
    start_time = time.time()
    results = model(img, verbose=False)
    end_time = time.time()
    
    duration_ms = (end_time - start_time) * 1000
    print(f"Tiempo de inferencia: {duration_ms:.2f} ms")
    
    if duration_ms > 100:
        print("DIAGNOSTICO: El sistema es LENTO. Probablemente por falta de GPU o modelo muy pesado.")
    else:
        print("DIAGNOSTICO: Velocidad ACEPTABLE.")
        
    print("-" * 40)
    print("FIN DEL DIAGNOSTICO")
    print("-" * 40)

if __name__ == "__main__":
    check_gpu_yolo()
