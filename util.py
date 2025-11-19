import logging
import os
import psutil

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Nivel mínimo de los mensajes que se registrarán
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato del mensaje
    handlers=[
        logging.FileHandler("app.log"),  # Guardar en un archivo log
        logging.StreamHandler()  # Mostrar en la consola
    ]
)

def log_event(message):
    try:
        with open(ruta, "a") as log_file:
            # Registrar la fecha y hora actual
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Escribir el mensaje en el archivo
            log_file.write(f"[{current_time}] {message}\n")
    except Exception as e:
        print(f"Error al escribir en el archivo log_eventos: {e}")
        
def get_raspberry_ip():
    try:
        # Ejecuta el comando hostname -I para obtener las direcciones IP
        ip_output = os.popen("hostname -I").read().strip()
        # Separa las IPs en una lista
        ip_list = ip_output.split()
        return ip_list
    except Exception as e:
        return f"Error al obtener las IPs: {e}"
    
def get_eth0_ip():
    try:
        # Ejecuta el comando para obtener información de 'eth0'
        result = os.popen("ip -4 addr show eth0 | grep inet").read().strip()
        if result:
            # Extrae la dirección IP de la salida del comando
            ip_address = result.split()[1].split('/')[0]
            return f"La dirección IP de eth0 es: {ip_address}"
        else:
            return "No se encontró una dirección IP para eth0. Asegúrate de que esté conectada."
    except Exception as e:
        return f"Error al obtener la dirección IP de eth0: {e}"
def extract_ip():
    try:
        # Ejecuta el comando para obtener información de 'eth0'
        result = os.popen("ip -4 addr show eth0 | grep inet").read().strip()
        if result:
            # Extrae la dirección IP de la salida del comando
            ip_address = result.split()[1].split('/')[0]
            return ip_address
        else:
            return "No IP."
    except Exception as e:
        return "Error eth0"
    
# Función para mostrar el estado de la memoria RAM
def mostrar_estado_memoria_cpu():
    memoria = psutil.virtual_memory()
    logging.info(f"Porcentaje de RAM usada: {memoria.percent}%")
    cpu_usage = psutil.cpu_percent(interval=1)
    logging.info(f"Uso de CPU:{cpu_usage}%")
#trae el clk en UTC