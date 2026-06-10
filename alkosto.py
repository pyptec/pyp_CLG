import subprocess
import time
import os
import RPi.GPIO as GPIO
import serial
import Temp
import util
import shlex
#import clock
from pathlib import Path
import modbus_relay

# constantes de programa
FORMATO_DATE="%d/%m/%Y %H:%M "

#-------------------------------------------------------------------
#pines de raspberry
#-------------------------------------------------------------------
GPIO_10_RELE=10
GPIO_06_PULSADOR = 6
GPIO_05_PILOTO =5



PATH_FILE="/home/pi/alkosto/reporte/reporte.txt"
PATH_FILE_AUDIO="/home/pi/alkosto/publicidad/"
PATH_AUDIO="/home/pi/alkosto/audio_ganador/001.mp3"
PATH_AUDIO_PUBLICIDAD="/home/pi/alkosto/publicidad/"
PATH_NO_SERIAL = " mplayer  /home/pi/alkosto/error/noSerial.mp3"
PATH_AUDIO_ERROR = "/home/pi/alkosto/error/noSerial.mp3"
TRAMA=")\r\n"

#Tiempo de temperatura de la raspberry
CHEQUEOTEMPERATURA = 60

# Tiempo de publicidades
PERIODO_PUBLICIDAD=900
SEC=1

# Índice actual de publicidad (inicia en 0)
IDX_PUBLICIDAD = 0

# Extensiones permitidas para publicidad
EXTS_PUBLICIDAD = {".mp3", ".wav", ".ogg"}

LISTA_AUDIO_PUBLICIDAD=-1


#Definiciones de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(GPIO_10_RELE, GPIO.OUT)
GPIO.setup(GPIO_05_PILOTO, GPIO.OUT)

GPIO.setup(GPIO_06_PULSADOR,GPIO.IN,pull_up_down=GPIO.PUD_UP)

MPLAYER = "/usr/bin/mplayer"  # ajusta si es necesario
MPLAYER_FLAGS = "-really-quiet -nolirc -nojoystick -noautosub -vo null -ao alsa -softvol -volume 85"

_player = None  # proceso actual (si quieres evitar solapes)

modbus_ctrl = None


def _spawn_player(path):
    global _player
    try:
        if not os.path.isfile(path):
            util.logging.error(f"Audio no encontrado: {path}")
            return

        # Evita solapar audios
        if _player and _player.poll() is None:
            util.logging.info("Ya hay audio reproduciéndose, se omite nuevo inicio.")
            return

        cmd = f'{MPLAYER} {MPLAYER_FLAGS} "{path}"'
        util.logging.info(f"Lanzando MPlayer: {cmd}")
        _player = subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    except Exception as e:
        util.logging.error(f"Error al lanzar reproductor: {e}")


########################################
#graba la hora del cmd serie del premio
########################################
def display(msj, data_serial=None):  
    reporte(msj)

    # El audio ya se lanza en background con _spawn_player()
    audio_ganador()

    if data_serial is None:
        util.logging.warning("No llegó número de cabina. No se activa Modbus.")
        return

    try:
        modbus_ctrl.activar_cabina_ganadora(data_serial)
    except Exception as e:
        util.logging.error(f"No se pudo activar cabina ganadora por Modbus: {e}")
        serial_a_modbus_off()
#def display(msj):  
#    reporte(msj)
#    rele_bombillo_on()
#    audio_ganador()
#    time.sleep(10)
#    rele_bombillo_off()
def on_hardware(msj):   
    print(msj + ' ' + time.strftime(FORMATO_DATE))
    reporte(msj)
def reporte(msj):
# se almacena los datos del ganador en un archivo txt
    file = open(PATH_FILE,'a')
    file.write('\n'+msj+time.strftime(FORMATO_DATE))
    file.close()
def audio_ganador():
      #subprocess.call(PATH_AUDIO.split())
     ruta = PATH_AUDIO   #os.path.join(PATH_AUDIO)
     util.logging.info(f"Audio Ganador: {ruta}")
     _spawn_player(ruta)
     #os.system(ruta )
def audio_publicida(msj):
    ruta = ruta = os.path.join(PATH_AUDIO_PUBLICIDAD, msj)#os.path.join(PATH_AUDIO_PUBLICIDAD+msj)
    #print(ruta)
    util.logging.info(f"Audio Publicidad: {ruta}")
    #os.system(ruta)
    _spawn_player(ruta)
def audio_error():
    ruta = PATH_AUDIO_ERROR#os.path.join(PATH_NO_SERIAL)
    util.logging.info(f"Audio Error (bg): {ruta}")
    #os.system(ruta)
    _spawn_player(ruta)

def rele_bombillo_on():
    GPIO.output(GPIO_05_PILOTO,True)
    GPIO.output(GPIO_10_RELE,True)
    util.logging.info("Rele_ON")
def rele_bombillo_off():
    GPIO.output(GPIO_05_PILOTO,False)
    GPIO.output(GPIO_10_RELE,False)
    util.logging.info("Rele_OFF")
    
def serial_a_modbus_on():
    # GPIO_10_RELE ahora actúa como selector RS232 / Modbus
    GPIO.output(GPIO_10_RELE, True)
    GPIO.output(GPIO_05_PILOTO, True)
    util.logging.info("Selector comunicación: MODO MODBUS RS485")

def serial_a_modbus_off():
    # Retorna el puerto a RS232 para escuchar la caja de pago
    GPIO.output(GPIO_10_RELE, False)
    GPIO.output(GPIO_05_PILOTO, False)
    util.logging.info("Selector comunicación: MODO RS232 CAJA/POS")
    
def CarpetaAudios():
  
    base = Path(PATH_FILE_AUDIO)
    if not base.exists():
        util.logging.warning(f"Carpeta de publicidad no existe: {base}")
        return []
    # Filtra solo archivos con extensiones válidas, ignora subcarpetas
    archivos = [
        p.name for p in sorted(base.iterdir())
        if p.is_file() and p.suffix.lower() in EXTS_PUBLICIDAD
    ]
    return archivos
   
def piloto_on():
    GPIO.output(GPIO_05_PILOTO,True)
def piloto_off():
    GPIO.output(GPIO_05_PILOTO,False)
def encendido():
    piloto_on()
    time.sleep(0.3)
    piloto_off()
    time.sleep(0.3) 
    piloto_on()
    time.sleep(0.3) 
    piloto_off()

        

    
try:
    UART = serial.Serial ("/dev/ttyS0", baudrate=9600, timeout=1)
except:
    Temp.on_hardware("No hay pto serie ")
    audio_error()
    exit
    
RELAY_CONFIG = modbus_relay.cargar_config("/home/pi/.scr/.scr/pyp_CLG/relay_config.yml")

try:
    UART = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)
except Exception as e:
    Temp.on_hardware("No hay pto serie ")
    util.logging.error(f"No se pudo abrir /dev/ttyS0: {e}")
    audio_error()
    raise SystemExit(1)

RELAY_CONFIG = modbus_relay.cargar_config("/home/pi/.scr/.scr/pyp_CLG/relay_config.yml")

modbus_ctrl = modbus_relay.ModbusRelayController(
    serial_port=UART,
    config=RELAY_CONFIG,
    switch_to_modbus=serial_a_modbus_on,
    switch_to_serial=serial_a_modbus_off,
    logger=util.logging
)
#------------------------------
# Funcion principal
#-----------------------------
def main():
    
    tempRaspberry = CHEQUEOTEMPERATURA
    timerPublicidad=PERIODO_PUBLICIDAD
    num_lista=LISTA_AUDIO_PUBLICIDAD
    idx_pub = IDX_PUBLICIDAD  # índice local que persistirá en el loop
    try:
        if UART.is_open:
            UART.reset_input_buffer()  
            UART.reset_output_buffer()  
    except AttributeError as e:
        print(f"Error: {e} - UART no tiene el atributo 'is_open'. Asegúrate de que UART esté correctamente inicializado. o conectado")
    except Exception as e:
        print(f"Se produjo un error: {e}")
    # rele off
    rele_bombillo_off()
    # Verificar la temperatura al inicio
    Temp.check_temp()
    
    #lista_audio =CarpetaAudios()
    #print(f"lista de audios {lista_audio}")
    #longAudios=len(lista_audio)
    #print(f"Longitud audios {str(longAudios)}")
    util.logging.info("Sistema CLG encendido.")
    #se inicia el wdt 
    Temp.iniciar_wdt()
    encendido()
    
    while True:
        
        time.sleep(1)
        timerPublicidad-=1
        tempRaspberry -= 1
        if UART.in_waiting > 0:
            try:
                # Leer los datos del puerto serie
                data = UART.read(UART.in_waiting)
                util.logging.info(f"DataRX (raw): {data}")
        
                # Decodificar los datos para eliminar los prefijos de bytes (b'')
                data = data.decode("utf-8").strip()
                util.logging.info(f"DataRX (decoded): {data}")
        
                # Visualizar el mensaje recibido
                # Reproduce audio ganador, conmuta a Modbus y activa cabina correspondiente
                display(f"Premio Ganador Cabina: {data} ", data)
                #display("Premio Ganador:")
            except UnicodeDecodeError as e:
                util.logging.error(f"Error de decodificación: {e}")
            except Exception as e:
                util.logging.error(f"Error procesando datos del puerto serie: {e}")
         
        elif GPIO.input(GPIO_06_PULSADOR) == 1: #0
             util.logging.info("mi premio PULSADOR")
             display("Premio Ganador: PULSADOR")  
        
        if timerPublicidad <= 0:
            timerPublicidad=PERIODO_PUBLICIDAD
            lista_audio = CarpetaAudios()  # refrescar en cada tick
            n = len(lista_audio)
            if n == 0:
                util.logging.warning("No hay audios de publicidad en la carpeta.")
            else:
                # Reajustar índice si la cantidad cambió
                if idx_pub >= n:
                    idx_pub = 0

                archivo = lista_audio[idx_pub]
                util.logging.info(f"Reproduciendo publicidad [{idx_pub+1}/{n}]: {archivo}")
                audio_publicida(archivo)

                # Avanzar a la siguiente, con wrap
                idx_pub = (idx_pub + 1) % n

        elif tempRaspberry <= 0:
            #se inicia el wdt 
            Temp.iniciar_wdt()
            tempRaspberry = CHEQUEOTEMPERATURA
            Temp.check_temp()
            util.logging.info(util.get_eth0_ip())
            util.mostrar_estado_memoria_cpu()
       
        
  
 

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Programa terminado.")