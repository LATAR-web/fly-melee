#!/usr/bin/env python3
"""
Fast multithreaded chunk downloader for Super Smash Bros Melee ISO
Compatible con Linux y Windows.
Incluye verificación previa: si la ISO ya existe en data/games/ssbm.iso,
no realiza ninguna descarga y finaliza inmediatamente.
"""
import os
import sys
import platform
import time
import threading
import urllib.request

# ==============================================================================
# Comprobación de Sistema Operativo (Linux o Windows - No incluye Mac)
# ==============================================================================
CURRENT_OS = platform.system()
if CURRENT_OS == "Linux":
    IS_LINUX = True
    IS_WINDOWS = False
elif CURRENT_OS == "Windows":
    IS_LINUX = False
    IS_WINDOWS = True
else:
    raise OSError(f"Sistema operativo no soportado: '{CURRENT_OS}'. Solo se admite Linux o Windows.")

URL = "https://ia801802.us.archive.org/33/items/multiplayer-games-are-made-to-be-shared/Super%20Smash%20Bros.%20Melee%20%28USA%29%20%28En%2CJa%29%20%28Rev%202%29.iso"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(PROJECT_DIR, "data", "games")
TARGET_FILE = os.path.join(TARGET_DIR, "ssbm.iso")
TOTAL_SIZE = 1459978240  # 1.359 GiB (Tamaño estándar NTSC v1.02)
NUM_WORKERS = 16

downloaded_bytes = 0
lock = threading.Lock()


def check_iso(filepath=TARGET_FILE):
    """
    Verifica si la ISO de Super Smash Bros. Melee ya existe y tiene un tamaño válido.
    Retorna True si existe y está completa, False si no existe o está incompleta.
    """
    if not os.path.exists(filepath):
        return False
    try:
        size = os.path.getsize(filepath)
        # Una ISO completa de Melee 1.02 tiene exactamente 1,459,978,240 bytes (o >= 1.4 GB sin comprimir)
        if size == TOTAL_SIZE or size >= 1400000000:
            return True
    except OSError:
        return False
    return False


# ==============================================================================
# LÓGICA PARA LINUX (USO DE POSIX pwrite)
# ==============================================================================
def download_chunk(worker_id, start, end, fd, failed_flag):
    global downloaded_bytes
    req = urllib.request.Request(URL)
    req.headers['Range'] = f'bytes={start}-{end}'
    req.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64)'

    retry_count = 0
    curr_pos = start
    while curr_pos <= end and retry_count < 10:
        try:
            req.headers['Range'] = f'bytes={curr_pos}-{end}'
            with urllib.request.urlopen(req, timeout=30) as resp:
                while curr_pos <= end:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    os.pwrite(fd, chunk, curr_pos)
                    chunk_len = len(chunk)
                    curr_pos += chunk_len
                    with lock:
                        downloaded_bytes += chunk_len
        except Exception:
            retry_count += 1
            time.sleep(1)

    if curr_pos <= end:
        failed_flag.set()


def main_linux():
    global downloaded_bytes
    downloaded_bytes = 0
    os.makedirs(TARGET_DIR, exist_ok=True)
    part_file = TARGET_FILE + ".part"

    # Pre-allocate file
    fd = os.open(part_file, os.O_RDWR | os.O_CREAT)
    os.ftruncate(fd, TOTAL_SIZE)

    chunk_size = TOTAL_SIZE // NUM_WORKERS
    threads = []
    failed_flag = threading.Event()

    start_time = time.time()
    print(f"🚀 Iniciando descarga multihilo ({NUM_WORKERS} conexiones) a {TARGET_FILE}...")

    for i in range(NUM_WORKERS):
        start = i * chunk_size
        end = TOTAL_SIZE - 1 if i == NUM_WORKERS - 1 else (start + chunk_size - 1)
        t = threading.Thread(target=download_chunk, args=(i, start, end, fd, failed_flag))
        t.daemon = True
        threads.append(t)
        t.start()

    # Progress monitor
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1.0)
            elapsed = time.time() - start_time
            with lock:
                current = downloaded_bytes
            speed_mb = (current / 1024 / 1024) / max(elapsed, 0.001)
            pct = min(100.0, (current / TOTAL_SIZE) * 100)
            eta = (TOTAL_SIZE - current) / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
            sys.stdout.write(f"\r📥 Progreso: {pct:.1f}% ({current // (1024*1024)}MB / {TOTAL_SIZE // (1024*1024)}MB) | Velocidad: {speed_mb:.2f} MB/s | ETA: {int(eta)}s  ")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\n⚠️ Descarga cancelada por el usuario.")
        os.close(fd)
        if os.path.exists(part_file):
            try:
                os.remove(part_file)
            except OSError:
                pass
        sys.exit(130)

    for t in threads:
        t.join()
    os.close(fd)

    if failed_flag.is_set():
        print("\n❌ Error: La descarga falló en uno o más fragmentos tras varios reintentos.")
        if os.path.exists(part_file):
            try:
                os.remove(part_file)
            except OSError:
                pass
        return 1

    if os.path.exists(TARGET_FILE):
        try:
            os.remove(TARGET_FILE)
        except OSError:
            pass
    os.replace(part_file, TARGET_FILE)

    final_size = os.path.getsize(TARGET_FILE)
    print(f"\n✅ Descarga completada: {final_size} bytes ({final_size / (1024*1024):.1f} MB) en {time.time() - start_time:.1f}s")
    return 0


# ==============================================================================
# FUNCIONES PARA WINDOWS (SIN os.pwrite, COMPATIBLE CON WIN32 I/O)
# ==============================================================================
def download_chunk_windows(worker_id, start, end, target_file, file_lock, failed_flag):
    global downloaded_bytes
    req = urllib.request.Request(URL)
    req.headers['Range'] = f'bytes={start}-{end}'
    req.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

    retry_count = 0
    curr_pos = start
    while curr_pos <= end and retry_count < 10:
        try:
            req.headers['Range'] = f'bytes={curr_pos}-{end}'
            with urllib.request.urlopen(req, timeout=30) as resp:
                while curr_pos <= end:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    chunk_len = len(chunk)
                    with file_lock:
                        with open(target_file, "r+b") as f:
                            f.seek(curr_pos)
                            f.write(chunk)
                    curr_pos += chunk_len
                    with lock:
                        downloaded_bytes += chunk_len
        except Exception:
            retry_count += 1
            time.sleep(1)

    if curr_pos <= end:
        failed_flag.set()


def main_windows():
    global downloaded_bytes
    downloaded_bytes = 0
    os.makedirs(TARGET_DIR, exist_ok=True)
    part_file = TARGET_FILE + ".part"

    # Pre-reservar archivo en Windows de forma binaria
    with open(part_file, "wb") as f:
        f.seek(TOTAL_SIZE - 1)
        f.write(b"\0")

    file_lock = threading.Lock()
    chunk_size = TOTAL_SIZE // NUM_WORKERS
    threads = []
    failed_flag = threading.Event()

    start_time = time.time()
    print(f"🚀 Iniciando descarga multihilo en Windows ({NUM_WORKERS} conexiones) a {TARGET_FILE}...")

    for i in range(NUM_WORKERS):
        start = i * chunk_size
        end = TOTAL_SIZE - 1 if i == NUM_WORKERS - 1 else (start + chunk_size - 1)
        t = threading.Thread(target=download_chunk_windows, args=(i, start, end, part_file, file_lock, failed_flag))
        t.daemon = True
        threads.append(t)
        t.start()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1.0)
            elapsed = time.time() - start_time
            with lock:
                current = downloaded_bytes
            speed_mb = (current / 1024 / 1024) / max(elapsed, 0.001)
            pct = min(100.0, (current / TOTAL_SIZE) * 100)
            eta = (TOTAL_SIZE - current) / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
            sys.stdout.write(f"\r📥 Progreso: {pct:.1f}% ({current // (1024*1024)}MB / {TOTAL_SIZE // (1024*1024)}MB) | Velocidad: {speed_mb:.2f} MB/s | ETA: {int(eta)}s  ")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\n⚠️ Descarga cancelada por el usuario.")
        if os.path.exists(part_file):
            try:
                os.remove(part_file)
            except OSError:
                pass
        sys.exit(130)

    for t in threads:
        t.join()

    if failed_flag.is_set():
        print("\n❌ Error: La descarga falló en uno o más fragmentos tras varios reintentos.")
        if os.path.exists(part_file):
            try:
                os.remove(part_file)
            except OSError:
                pass
        return 1

    if os.path.exists(TARGET_FILE):
        try:
            os.remove(TARGET_FILE)
        except OSError:
            pass
    os.replace(part_file, TARGET_FILE)

    final_size = os.path.getsize(TARGET_FILE)
    print(f"\n✅ Descarga completada en Windows: {final_size} bytes ({final_size / (1024*1024):.1f} MB) en {time.time() - start_time:.1f}s")
    return 0


# ==============================================================================
# COMPROBACIÓN PRINCIPAL
# ==============================================================================
def check_or_download():
    force = "--force" in sys.argv or "-f" in sys.argv

    if not force and check_iso(TARGET_FILE):
        size = os.path.getsize(TARGET_FILE)
        print("✅ [ISO Melee] La ISO de Super Smash Bros. Melee ya existe y está verificada:")
        print(f"   📁 {TARGET_FILE} ({size / (1024 * 1024):.1f} MB)")
        print("   No es necesario descargar de nuevo.")
        return 0

    if os.path.exists(TARGET_FILE):
        size = os.path.getsize(TARGET_FILE)
        print(f"⚠️ [ISO Melee] Archivo incompleto o tamaño inválido ({size} bytes de {TOTAL_SIZE}).")
        print("   Se procederá a descargar la versión completa...")
        try:
            os.remove(TARGET_FILE)
        except OSError:
            pass

    print("=" * 72)
    print("  📥 DESCARGA AUTOMÁTICA DE SUPER SMASH BROS. MELEE (ISO)")
    print(f"  Destino: {TARGET_FILE}")
    print(f"  Tamaño: {TOTAL_SIZE / (1024 * 1024):.1f} MB | Conexiones: {NUM_WORKERS}")
    print("=" * 72)

    if IS_WINDOWS:
        return main_windows()
    else:
        return main_linux()


def main():
    res = check_or_download()
    sys.exit(res if res is not None else 0)


if __name__ == "__main__":
    main()
