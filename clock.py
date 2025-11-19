

import math
import time
import datetime
from demo_opts import get_device
from luma.core.render import canvas
import os
import threading
device = None

def posn(angle, arm_length):
    dx = int(math.cos(math.radians(angle)) * arm_length)
    dy = int(math.sin(math.radians(angle)) * arm_length)
    return (dx, dy)
def initialize_device():
    """Inicializa el dispositivo en un hilo separado."""
    global device
    try:
        device = get_device()
        print("Dispositivo inicializado correctamente.")
    except Exception as e:
        print(f"Error al inicializar el dispositivo: {e}")
def extract_ip():
    """Obtiene la IP del dispositivo en 'eth0'."""
    try:
        result = os.popen("ip -4 addr show eth0 | grep inet").read().strip()
        if result:
            return result.split()[1].split('/')[0]
        else:
            return "No IP."
    except Exception as e:
        return f"Error eth0: {e}"

def iniLcd():
    """Inicia el hilo para inicializar el dispositivo."""
    device_thread = threading.Thread(target=initialize_device)
    device_thread.start()
def timerLcd():
    """Inicia el hilo para mostrar el reloj."""
    thread = threading.Thread(target=display_clock, daemon=True)
    thread.start()
        
def display_clock():
    """Función para mostrar la hora, fecha e IP en el display."""
    
    global device
    today_last_time = "Unknown"
    while True:
        if device is None:
            print("Esperando que el dispositivo se inicialice...")
            time.sleep(1)
            continue
        now = datetime.datetime.now()
        today_date = now.strftime("%d %b %y")
        today_time = now.strftime("%H:%M:%S")
        ip = extract_ip()
        if today_time != today_last_time:
            today_last_time = today_time
            with canvas(device) as draw:
                now = datetime.datetime.now()
                today_date = now.strftime("%d %b %y")

                margin = 4

                cx = 30
                cy = min(device.height, 64) / 2

                left = cx - cy
                right = cx + cy

                hrs_angle = 270 + (30 * (now.hour + (now.minute / 60.0)))
                hrs = posn(hrs_angle, cy - margin - 7)

                min_angle = 270 + (6 * now.minute)
                mins = posn(min_angle, cy - margin - 2)

                sec_angle = 270 + (6 * now.second)
                secs = posn(sec_angle, cy - margin - 2)

                draw.ellipse((left + margin, margin, right - margin, min(device.height, 64) - margin), outline="white")
                draw.line((cx, cy, cx + hrs[0], cy + hrs[1]), fill="white")
                draw.line((cx, cy, cx + mins[0], cy + mins[1]), fill="white")
                draw.line((cx, cy, cx + secs[0], cy + secs[1]), fill="red")
                draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill="white", outline="white")
                draw.text((2 * (cx-5 + margin), cy - 28), "Alkosto CLG", fill="yellow")
                draw.text((2 * (cx-5 + margin), cy - 18), ip, fill="yellow")
                draw.text((2 * (cx + margin), cy - 4), today_date, fill="yellow")
                draw.text((2 * (cx + margin), cy+10), today_time, fill="yellow")

        time.sleep(0.1)


#if __name__ == "__main__":
#    try:
#        device = get_device()
#        main()
#    except KeyboardInterrupt:
#        pass


