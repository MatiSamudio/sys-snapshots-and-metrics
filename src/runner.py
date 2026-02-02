import time
import logging
import collector
import storage

def run_capture(config: dict, db_path: str) -> None:
    intervalo = config.get("interval", 5)
    duracion = config.get("duration", 60)
    
    # Calculamos cuántas veces se ejecutará (Punto 2.1)
    total_ticks = int(duracion / intervalo)
    
    ultimo_snapshot = None
    
    logging.info(f"Iniciando captura: {total_ticks} ticks programados.")

    for i in range(total_ticks):
        try:
            # 1. Recolectar (Llama a collector)
            # Pasamos el último para que el collector calcule los deltas internamente
            snapshot_actual = collector.get_snapshot(ultimo_snapshot)
            
            # 2. Guardar (Punto 2.2.5)
            storage.save_snapshot(db_path, snapshot_actual)
            
            # 3. Actualizar memoria para el siguiente delta
            ultimo_snapshot = snapshot_actual
            
            logging.info(f"Tick {i+1}/{total_ticks} completado.")

        except Exception as e:
            # 4. Resiliencia (Punto 3: Log y sigue)
            logging.error(f"Fallo en tick {i+1}: {e}. El runner continúa.")

        # 5. Ritmo
        time.sleep(intervalo)

    logging.info("Captura finalizada exitosamente.")
