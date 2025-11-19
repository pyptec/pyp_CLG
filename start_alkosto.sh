 
#!/bin/bash
set -e  # Si falla algo, el script termina inmediatamente
VENV_DIR="alkosto"
echo "======================================"
echo "Iniciando instalación del entorno"
echo "======================================"
# 1. Verificar si ya existe el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "  No existe entorno virtual. Creando en $VENV_DIR ..."
    python3 -m venv --system-site-packages "$VENV_DIR"
else
    echo "El entorno virtual ya existe en $VENV_DIR"
fi
# 2. Activar el entorno virtual
echo "  Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# 4. Instalar dependencias
if [ -f "requirements.txt" ]; then
    echo "Instalando dependencias desde requirements.txt..."
    sudo apt install -y python3-dev python3-pip build-essential gcc
    sudo apt-get install mplayer
    pip install -r requirements.txt
else
    echo "No se encontró requirements.txt, omitiendo instalación de dependencias."
fi
echo "======================================"
echo "Instalación completada con éxito!"
echo "======================================"
 
 