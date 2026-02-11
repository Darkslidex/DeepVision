Write-Host "INICIANDO PROTOCOLO DE REINICIO NUCLEAR DEL ENTORNO..." -ForegroundColor Red

# 1. Destrucción
if (Test-Path ".venv") {
    Write-Host "Eliminando entorno virtual corrupto..." -ForegroundColor Yellow
    Remove-Item ".venv" -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path "mediapipe.py") {
    Write-Host "Eliminando archivo mediapipe.py conflictivo..." -ForegroundColor Yellow
    Remove-Item "mediapipe.py" -Force -ErrorAction SilentlyContinue
}

# 2. Creación
Write-Host "Creando nuevo entorno virtual limpio..." -ForegroundColor Green
python -m venv .venv

# 3. Instalación Blindada
Write-Host "Instalando dependencias blindadas (The Golden Combo)..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install mediapipe==0.10.9 protobuf==3.20.3 opencv-python

# 4. Verificación
Write-Host "Ejecutando prueba de verificación..." -ForegroundColor Magenta
if (Test-Path "test_face.py") {
    & .\.venv\Scripts\python.exe test_face.py
} else {
    Write-Host "No se encontró test_face.py para verificar." -ForegroundColor Red
}

Write-Host "PROCESO COMPLETADO. SI VES EL VIDEO, TODO FUNCIONA." -ForegroundColor Green
PAUSE
