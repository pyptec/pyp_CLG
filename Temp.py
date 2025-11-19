import subprocess
import time
import RPi.GPIO as GPIO
import util
import threading

# constantes de programa
FORMATO_DATE="%d/%m/%Y %H:%M "
GPIO_11_VENTILADOR=11
GPIO_23_WDI=23

PERIODO_PUBLICIDAD=1
SEC=60

#Definiciones de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(GPIO_11_VENTILADOR, GPIO.OUT)
GPIO.setup(GPIO_23_WDI, GPIO.OUT)



def on_hardware(msj):   
    print(msj + ' ' + time.strftime(FORMATO_DATE))
#######################################
#Mantenimiento raspberry Temperatura
########################################
def cpu_temp():
	thermal_zone = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=subprocess.PIPE)
	out, err = thermal_zone.communicate()
	cpu_temp = int(out.decode())/1000
	return cpu_temp

########################################################
#Se chequea Temperatura y se apaga/prende el ventilador
########################################################
def check_temp():
	cpu = cpu_temp()
	#on_hardware("Temperatura: "+str(cpu))
	if (float(cpu) > 48.0 ) :
		GPIO.output(GPIO_11_VENTILADOR, True)
		util.logging.info("CPU ALTA: " + str(cpu) + "º")
		#on_hardware("CPU ALTA: "+str(cpu)+"º\n ")
	else: 
		GPIO.output(GPIO_11_VENTILADOR, False)
		#on_hardware("CPU BAJA: "+str(cpu)+"º\n ")
		util.logging.info("CPU BAJA: " + str(cpu) + "º")

	


def wdt():
    util.logging.info("WDT:INICIADO")
    GPIO.output(GPIO_23_WDI, True)
    time.sleep(0.2)
    GPIO.output(GPIO_23_WDI, False)
    time.sleep(0.2)
def iniciar_wdt():
    # Crear y empezar el hilo que ejecutará la función wdt
    hilo_wdt = threading.Thread(target=wdt)
    hilo_wdt.daemon = True  # El hilo se cerrará automáticamente cuando termine el programa principal
    hilo_wdt.start()