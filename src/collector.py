def collect_top_processes(top_n: int) -> list[dict]:  #Recibe un parámetro top_n (cantidad de procesos que quieres en el ranking) y devuelve una lista de diccionarios con información de procesos.
    procesos = []

    # Primer muestreo de CPU (necesario para que cpu_percent tenga datos reales)
    for proc in psutil.process_iter(['pid', 'name']):  #Recorre todos los procesos activos y pide: pid (identificador del proceso) y name (nombre).
        try:
            proc.cpu_percent(interval=None) #para inicializar la medición de CPU (la primera llamada siempre da 0, sirve para preparar el muestreo).
        except (psutil.NoSuchProcess, psutil.AccessDenied): #para ignorar procesos que ya terminaron (NoSuchProcess) o a los que no tienes permiso (AccessDenied).
            continue

    # Segundo muestreo con intervalo para obtener valores actualizados
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            cpu = proc.cpu_percent(interval=0.1)  # muestreo rápido, mide el % de CPU en intervalo corto de 0.1 seg
            mem = proc.memory_info().rss / (1024**2)  # devuelve la memoria RAM usada por el proceso en bytes
            procesos.append({  #Se guarda la información en un diccionario con claves
                "pid": proc.info['pid'],
                "nombre": proc.info['name'] or "desconocido", #Si el nombre es None, se reemplaza por "desconocido"
                "cpu_percent": cpu or 0.0, #Si CPU o RAM son None, se normalizan a 0.0
                "ram_mb": mem or 0.0
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue #Si el proceso ya no existe o no tienes permiso, se ignora con continue

    # Normalizar: si algún valor es None, lo pasamos a 0
    for p in procesos:
        p["cpu_percent"] = p.get("cpu_percent", 0.0) 
        p["ram_mb"] = p.get("ram_mb", 0.0)

    # Ordena 2 veces, por CPU y RAM
    top_cpu = sorted(procesos, key=lambda x: x["cpu_percent"], reverse=True)[:top_n] #[:top_n]: toma solo los primeros top_n procesos.
    top_ram = sorted(procesos, key=lambda x: x["ram_mb"], reverse=True)[:top_n] #reverse=True: orden descendente (mayor a menor).

    # Combinar resultados en una sola lista
    resultado = {
        "top_cpu": top_cpu,
        "top_ram": top_ram
    }
    return resultado
