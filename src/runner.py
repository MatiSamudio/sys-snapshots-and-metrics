#agregar para buen funcionamiento:libreria psutil, sqlite


import time#libreria que permite el calculo de tiempo y los intervalos
import logging#esto nos permite mandar menjases muy detallados por categoria
import collector#llamamos a recolector de datos
import storage#llamamos a la base de datos

def run_capture(config: dict, db_path: str) -> None:#aca  definimos una funcion que le dice a python que va a recibir un diccionario con intervalos y duracion y tamben le da la dirrecion de la base de datos
   
    intervalo = config.get("interval", 5)#aca permitimos al usuario 5 que le de cada cuanto quiere el chequeo sino lo configura python asume un intervalo de 5 segundos
   
    duracion = config.get("duration", 60)#aca le decimos permitimos al usuario cargar una duracion sino directamente python asume 60segundos 
    
    # Calculamos cuántas veces se ejecutará (Punto 2.1)
    total_ticks = int(duracion / intervalo)
    
    # Memoria para el "snapshot anterior" (Punto 2.2.4)
    ultimo_snapshot = None
    
    logging.info(f"Iniciando captura: {total_ticks} ticks programados.")#informamos del tick se esta realizando

    for i in range(total_ticks):
        try:
            # 1. Recolectar (Llama a collector)
            # Pasamos el último para que el collector calcule los deltas internamente
            snapshot_actual = collector.get_snapshot(ultimo_snapshot)
            
            # 2. Guardar (Punto 2.2.5)
            storage.save_snapshot(db_path, snapshot_actual)
            
            # 3. Actualizar memoria para el siguiente delta
            ultimo_snapshot = snapshot_actual
            
            logging.info(f"Tick {i+1}/{total_ticks} completado.")#informamos de los ticks completados

        except Exception as e:
            # 4. Resiliencia (Punto 3: Log y sigue)
            logging.error(f"Fallo en tick {i+1}: {e}. El runner continúa.")

        # 5. Ritmo
        time.sleep(intervalo)#nos permite editar la cantidad de segundos que habra por cada tick

    logging.info("Captura finalizada exitosamente.")

