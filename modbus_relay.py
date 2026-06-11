import time
import re
import yaml


def cargar_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalizar_cabina(data):
    """
    Extrae el número de cabina recibido por serial.
    Ejemplos:
    '01'       -> '01'
    '1'        -> '01'
    'Cabina 1' -> '01'
    'CAJA 05)' -> '05'
    """
    if data is None:
        return None

    texto = str(data).strip()
    numeros = re.findall(r"\d+", texto)

    if not numeros:
        return None

    numero = int(numeros[0])
    return f"{numero:02d}"


def crc16_modbus(data: bytes) -> bytes:
    """
    Calcula CRC16 Modbus RTU.
    Retorna CRC en orden Low Byte, High Byte.
    """
    crc = 0xFFFF

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1

    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def build_write_coil(slave_id, coil_address, state):
    """
    Función Modbus 05 - Write Single Coil.
    ON  = FF00
    OFF = 0000
    """
    value = 0xFF00 if state else 0x0000

    frame = bytes([
        slave_id & 0xFF,
        0x05,
        (coil_address >> 8) & 0xFF,
        coil_address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])

    return frame + crc16_modbus(frame)


class ModbusRelayController:
    def __init__(self, serial_port, config, switch_to_modbus, switch_to_serial, logger):
        self.serial_port = serial_port
        self.config = config
        self.switch_to_modbus = switch_to_modbus
        self.switch_to_serial = switch_to_serial
        self.logger = logger

        self.modbus_cfg = config.get("modbus", {})
        self.evento_cfg = config.get("evento_ganador", {})
        self.selector_cfg = config.get("selector", {})
        self.cabinas = config.get("cabinas", {})

        self.coil_address = int(self.modbus_cfg.get("coil_address", 0))
        self.stabilization_time = float(self.selector_cfg.get("stabilization_time_sec", 0.35))

    def buscar_cabina(self, data_serial):
        cabina_id = normalizar_cabina(data_serial)

        if cabina_id is None:
            raise ValueError(f"No se pudo extraer número de cabina desde: {data_serial}")

        cabina = self.cabinas.get(cabina_id)

        if not cabina:
            raise ValueError(f"Cabina no configurada en YAML: {cabina_id}")

        if not cabina.get("enabled", True):
            raise ValueError(f"Cabina deshabilitada en YAML: {cabina_id}")

        slave_id = int(cabina["slave_id"])
        nombre = cabina.get("nombre", f"Cabina {cabina_id}")

        return cabina_id, nombre, slave_id

    def enviar_coil(self, slave_id, state):
        frame = build_write_coil(
            slave_id=slave_id,
            coil_address=self.coil_address,
            state=state
        )

        self.logger.info(
            f"Modbus TX slave={slave_id} coil={self.coil_address} state={state} frame={frame.hex(' ').upper()}"
        )

        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()
        self.serial_port.write(frame)
        self.serial_port.flush()

        time.sleep(0.15)

        # Si el módulo responde, se lee la respuesta. Si no responde, no bloquea demasiado.
        respuesta = b""
        try:
            if self.serial_port.in_waiting > 0:
                respuesta = self.serial_port.read(self.serial_port.in_waiting)
                self.logger.info(f"Modbus RX: {respuesta.hex(' ').upper()}")
        except Exception as e:
            self.logger.warning(f"No se pudo leer respuesta Modbus: {e}")

        return respuesta

    def relay_on(self, slave_id):
        return self.enviar_coil(slave_id, True)

    def relay_off(self, slave_id):
        return self.enviar_coil(slave_id, False)

    def activar_cabina_ganadora(self, data_serial):
        cabina_id, nombre, slave_id = self.buscar_cabina(data_serial)

        total = int(self.evento_cfg.get("tiempo_total_seg", 120))
        on_time = float(self.evento_cfg.get("tiempo_on_seg", 2))
        off_time = float(self.evento_cfg.get("tiempo_off_seg", 2))
        apagar_final = bool(self.evento_cfg.get("apagar_rele_al_finalizar", True))

        self.logger.info(
            f"Evento ganador: {nombre} / cabina_id={cabina_id} / slave_id={slave_id}"
        )

        # Conmuta físicamente el puerto: RS232 -> Modbus RS485
        self.switch_to_modbus()
        time.sleep(self.stabilization_time)

        inicio = time.time()

        try:
            while (time.time() - inicio) < total:
                self.relay_on(slave_id)
                time.sleep(on_time)

                #self.relay_off(slave_id)
                #time.sleep(off_time)

        except Exception as e:
            self.logger.error(f"Error durante titileo Modbus de {nombre}: {e}")

        finally:
            if apagar_final:
                try:
                    self.relay_off(slave_id)
                except Exception as e:
                    self.logger.error(f"No se pudo apagar relé final de {nombre}: {e}")

            time.sleep(0.1)

            # Devuelve físicamente el puerto: Modbus RS485 -> RS232 caja de pago
            self.switch_to_serial()
            time.sleep(self.stabilization_time)

            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except Exception:
                pass

            self.logger.info(f"Evento ganador finalizado: {nombre}")