$ErrorActionPreference = "Stop"

Write-Host ">>> INICIANDO PROTOCOLO DE REINICIO DE DEEPVISION (NUKE & PAVE) <<<" -ForegroundColor Cyan

$VenvDir = ".venv"

# 1. Eliminar entorno virtual anterior si existe
if (Test-Path $VenvDir) {
    Write-Host "1. Detectado entorno virtual corrupto/antiguo. Eliminando..." -ForegroundColor Yellow
    Remove-Item -Path $VenvDir -Recurse -Force
    Write-Host "   Entorno eliminado." -ForegroundColor Green
}
else {
    Write-Host "1. No se detectó entorno previo. Continuando." -ForegroundColor Gray
}

# 2. Crear nuevo entorno virtual
Write-Host "2. Creando nuevo entorno virtual aislado (.venv)..." -ForegroundColor Yellow
python -m venv $VenvDir
if (-not (Test-Path $VenvDir)) {
    Write-Host "ERROR CRÍTICO: No se pudo crear la carpeta .venv. Verifique permisos o instalación de Python." -ForegroundColor Red
    exit 1
}
Write-Host "   Entorno creado exitosamente." -ForegroundColor Green

# 3. Activar entorno virtual e instalar dependencias
Write-Host "3. Instalando dependencias críticas en el nuevo entorno..." -ForegroundColor Yellow

# Definir ruta al pip del entorno virtual
$PipExe = ".\$VenvDir\Scripts\python.exe -m pip"
$PythonExe = ".\$VenvDir\Scripts\python.exe"

# Actualizar pip
Write-Host "   Actualizando pip..." -ForegroundColor DarkGray
Invoke-Expression "$PipExe install --upgrade pip"

# 4. Instalar PyTorch con soporte CUDA 12.1 (CRÍTICO PARA RTX 2060)
Write-Host "4. Instalando PyTorch con aceleración CUDA 12.1..." -ForegroundColor Magenta
# Usamos --index-url para asegurar la versión de CUDA correcta
Invoke-Expression "$PipExe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"

# 5. Instalar resto de librerías
Write-Host "5. Instalando Ultralytics, OpenCV, PyQt6, MediaPipe..." -ForegroundColor Magenta


# Corrected line for dependencies
Invoke-Expression "$PipExe install ultralytics opencv-python PyQt6 mediapipe psutil"

# 6. Verificación
Write-Host "6. Ejecutando diagnóstico de sistema..." -ForegroundColor Cyan
if (Test-Path "check_environment.py") {
    Invoke-Expression "$PythonExe check_environment.py"
}
else {
    Write-Host "ADVERTENCIA: No se encontró check_environment.py para verificar." -ForegroundColor Yellow
}

Write-Host "`n>>> PROCESO COMPLETADO. Si todo está en VERDE, el sistema está listo. <<<" -ForegroundColor Green
Pause
