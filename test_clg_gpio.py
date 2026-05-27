#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
import sys
import select

# Pines BCM según alkosto.py
GPIO_RELE = 10
GPIO_PULSADOR = 6
GPIO_PILOTO = 5

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(GPIO_RELE, GPIO.OUT)
GPIO.setup(GPIO_PILOTO, GPIO.OUT)
GPIO.setup(GPIO_PULSADOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def estado_pin(pin):
    return GPIO.input(pin)

def mostrar_estado():
    rele = estado_pin(GPIO_RELE)
    piloto = estado_pin(GPIO_PILOTO)
    pulsador = estado_pin(GPIO_PULSADOR)

    print("\n--- ESTADO CLG ---")
    print(f"Relé GPIO{GPIO_RELE}:      {'ON' if rele else 'OFF'}")
    print(f"Piloto GPIO{GPIO_PILOTO}:  {'ON' if piloto else 'OFF'}")
    print(f"Pulsador GPIO{GPIO_PULSADOR}: {'LIBRE' if pulsador else 'PRESIONADO'}")
    print("------------------")

def rele_on():
    GPIO.output(GPIO_RELE, True)
    print("Relé ON")

def rele_off():
    GPIO.output(GPIO_RELE, False)
    print("Relé OFF")

def piloto_on():
    GPIO.output(GPIO_PILOTO, True)
    print("Piloto ON")

def piloto_off():
    GPIO.output(GPIO_PILOTO, False)
    print("Piloto OFF")

def activar_ganador(segundos=5):
    print(f"Activando relé + piloto por {segundos} segundos...")
    GPIO.output(GPIO_RELE, True)
    GPIO.output(GPIO_PILOTO, True)
    time.sleep(segundos)
    GPIO.output(GPIO_RELE, False)
    GPIO.output(GPIO_PILOTO, False)
    print("Secuencia terminada.")

def monitorear_pulsador():
    print("Monitoreando pulsador. Presiona 'q' + Enter para volver al menú.")
    print("Nota: con PUD_UP, normalmente LIBRE=1 y PRESIONADO=0")

    while True:
        estado = GPIO.input(GPIO_PULSADOR)

        if estado == 0:
            texto = "PRESIONADO"
        else:
            texto = "LIBRE"

        print(f"GPIO{GPIO_PULSADOR} = {estado} → {texto}")

        # Permite salir sin Ctrl+C
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            tecla = input().strip().lower()
            if tecla == "q":
                print("Volviendo al menú...")
                break

        time.sleep(0.5)

try:
    while True:
        print("""
1. Ver estado
2. Encender relé
3. Apagar relé
4. Encender piloto
5. Apagar piloto
6. Activar ganador 5 segundos
7. Monitorear pulsador
8. Apagar todo
0. Salir
""")
        op = input("Seleccione opción: ").strip()

        if op == "1":
            mostrar_estado()
        elif op == "2":
            rele_on()
        elif op == "3":
            rele_off()
        elif op == "4":
            piloto_on()
        elif op == "5":
            piloto_off()
        elif op == "6":
            activar_ganador(5)
        elif op == "7":
            monitorear_pulsador()
        elif op == "8":
            GPIO.output(GPIO_RELE, False)
            GPIO.output(GPIO_PILOTO, False)
            print("Relé y piloto apagados.")
        elif op == "0":
            break
        else:
            print("Opción no válida.")

except KeyboardInterrupt:
    print("\nSaliendo...")

finally:
    GPIO.output(GPIO_RELE, False)
    GPIO.output(GPIO_PILOTO, False)
    GPIO.cleanup()
    print("GPIO liberados.")