#!/usr/bin/env python3
"""
Fast multithreaded chunk downloader for Super Smash Bros Melee ISO
"""
import os
import sys
import time
import threading
import urllib.request

URL = "https://ia801802.us.archive.org/33/items/multiplayer-games-are-made-to-be-shared/Super%20Smash%20Bros.%20Melee%20%28USA%29%20%28En%2CJa%29%20%28Rev%202%29.iso"
TARGET_FILE = "/home/ltar/projects/fly-melee/data/games/ssbm.iso"
TOTAL_SIZE = 1459978240
NUM_WORKERS = 16

downloaded_bytes = 0
lock = threading.Lock()

def download_chunk(worker_id, start, end, fd):
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
        except Exception as e:
            retry_count += 1
            time.sleep(1)

def main():
    global downloaded_bytes
    os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
    
    # Pre-allocate file
    fd = os.open(TARGET_FILE, os.O_RDWR | os.O_CREAT)
    os.ftruncate(fd, TOTAL_SIZE)

    chunk_size = TOTAL_SIZE // NUM_WORKERS
    threads = []
    
    start_time = time.time()
    print(f"🚀 Iniciando descarga multihilo ({NUM_WORKERS} conexiones) a {TARGET_FILE}...")

    for i in range(NUM_WORKERS):
        start = i * chunk_size
        end = TOTAL_SIZE - 1 if i == NUM_WORKERS - 1 else (start + chunk_size - 1)
        t = threading.Thread(target=download_chunk, args=(i, start, end, fd))
        t.daemon = True
        threads.append(t)
        t.start()

    # Progress monitor
    while any(t.is_alive() for t in threads):
        time.sleep(1.0)
        elapsed = time.time() - start_time
        with lock:
            current = downloaded_bytes
        speed_mb = (current / 1024 / 1024) / max(elapsed, 0.001)
        pct = (current / TOTAL_SIZE) * 100
        eta = (TOTAL_SIZE - current) / (speed_mb * 1024 * 1024) if speed_mb > 0 else 0
        sys.stdout.write(f"\r📥 Progreso: {pct:.1f}% ({current // (1024*1024)}MB / {TOTAL_SIZE // (1024*1024)}MB) | Velocidad: {speed_mb:.2f} MB/s | ETA: {int(eta)}s  ")
        sys.stdout.flush()

    for t in threads:
        t.join()
    os.close(fd)
    
    final_size = os.path.getsize(TARGET_FILE)
    print(f"\n✅ Descarga completada: {final_size} bytes ({final_size / (1024*1024):.1f} MB) en {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    main()
