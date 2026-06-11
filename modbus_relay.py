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
    '01'        -> '01'
    '1'         -> '01'
    'Cabina 1'  -> '01'
    'CAJA 05)'  -> '05'
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

    Se mantiene para apagado final de seguridad.
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


def build_flash_on(slave_id, relay_address=0x0003, delay_seconds=2):
    """
    Función Modbus 16 / 0x10 - Flash ON con timer interno del módulo.

    Ejemplo para slave_id=1 y delay_seconds=2:
    01 10 00 03 00 02 04 00 04 00 14 F2 74

    relay_address:
        Para relé 1 en modo flash ON, el manual usa 0x0003.

    delay_seconds:
        El módulo usa base de 0.1 segundos.
        2 segundos = 20 decimal = 0x0014.
    """
    delay_value = int(delay_seconds * 10)

    frame = bytes([
        slave_id & 0xFF,
        0x10,
        (relay_address >> 8) & 0xFF,
        relay_address & 0xFF,
        0x00,
        0x02,
        0x04,
        0x00,
        0x04,
        (delay_value >> 8) & 0xFF,
        delay_value & 0xFF,
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

        # Coil 0 para apagado manual de seguridad con función 05
        self.coil_address = int(self.modbus_cfg.get("coil_address", 0))

        # Dirección interna del modo flash ON para relé 1
        self.flash_relay_address = int(self.modbus_cfg.get("flash_relay_address", 0x0003))

        # Tiempo para que el relé físico conmute RS232 <-> RS485 antes de transmitir
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

    def _enviar_frame(self, frame, descripcion="Modbus TX"):
        """
        Envía una trama Modbus RTU por el mismo puerto serial.
        El puerto ya debe estar conmutado físicamente a RS485.
        """
        self.logger.info(f"{descripcion}: {frame.hex(' ').upper()}")

        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()
        self.serial_port.write(frame)
        self.serial_port.flush()

        time.sleep(0.15)

        respuesta = b""
        try:
            if self.serial_port.in_waiting > 0:
                respuesta = self.serial_port.read(self.serial_port.in_waiting)
                #self.logger.info(f"Modbus RX: {respuesta.hex(' ').upper()}")
        except Exception as e:
            self.logger.warning(f"No se pudo leer respuesta Modbus: {e}")

        return respuesta

    def enviar_coil(self, slave_id, state):
        """
        Envía ON/OFF manual con función 05.
        Se usa principalmente para apagado final de seguridad.
        """
        frame = build_write_coil(
            slave_id=slave_id,
            coil_address=self.coil_address,
            state=state
        )

        estado = "ON" if state else "OFF"
        return self._enviar_frame(
            frame,
            descripcion=f"Modbus COIL {estado} slave={slave_id} coil={self.coil_address}"
        )

    def relay_on(self, slave_id):
        return self.enviar_coil(slave_id, True)

    def relay_off(self, slave_id):
        return self.enviar_coil(slave_id, False)

    def relay_flash_on(self, slave_id, delay_seconds=2):
        """
        Envía un solo comando flash ON.
        El módulo prende el relé y lo apaga automáticamente al cumplirse el tiempo.

        Para slave_id=1 y delay_seconds=2 debe generar:
        01 10 00 03 00 02 04 00 04 00 14 F2 74
        """
        frame = build_flash_on(
            slave_id=slave_id,
            relay_address=self.flash_relay_address,
            delay_seconds=delay_seconds
        )

        return self._enviar_frame(
            frame,
            descripcion=f"Modbus FLASH_ON slave={slave_id} delay={delay_seconds}s"
        )

    def activar_cabina_ganadora(self, data_serial):
        """
        Flujo completo:
        1. Recibe dato serial de cabina.
        2. Busca cabina en YAML.
        3. Conmuta puerto físico RS232 -> RS485 Modbus.
        4. Envía comando flash ON cada ciclo.
        5. Mantiene la bombona titilando durante el tiempo configurado.
        6. Apaga relé remoto como seguridad.
        7. Conmuta puerto físico RS485 -> RS232.
        """
        cabina_id, nombre, slave_id = self.buscar_cabina(data_serial)

        total = int(self.evento_cfg.get("tiempo_total_seg", 120))
        on_time = float(self.evento_cfg.get("tiempo_on_seg", 2))
        off_time = float(self.evento_cfg.get("tiempo_off_seg", 2))
        apagar_final = bool(self.evento_cfg.get("apagar_rele_al_finalizar", True))

        self.logger.info(
            f"Evento ganador: {nombre} / cabina_id={cabina_id} / slave_id={slave_id}"
        )

        # Conmuta físicamente el puerto: RS232 caja/POS -> Modbus RS485
        self.switch_to_modbus()
        time.sleep(self.stabilization_time)

        inicio = time.time()

        try:
            while (time.time() - inicio) < total:
                # Nuevo método:
                # Un solo comando prende el relé y el módulo lo apaga solo.
                self.relay_flash_on(slave_id, delay_seconds=on_time)

                # Espera el tiempo prendido + la pausa apagado.
                # Ejemplo: 2s ON automático + 2s OFF = ciclo de 4s.
                time.sleep(on_time + off_time)

        except Exception as e:
            self.logger.error(f"Error durante titileo Modbus de {nombre}: {e}")

        finally:
            # Apagado manual de seguridad.
            # Aunque el flash ON se apaga solo, esto garantiza estado OFF al finalizar.
            if apagar_final:
                try:
                    self.relay_off(slave_id)
                except Exception as e:
                    self.logger.error(f"No se pudo apagar relé final de {nombre}: {e}")

            time.sleep(0.1)

            # Devuelve físicamente el puerto: Modbus RS485 -> RS232 caja/POS
            self.switch_to_serial()
            time.sleep(self.stabilization_time)

            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except Exception:
                pass

            self.logger.info(f"Evento ganador finalizado: {nombre}")