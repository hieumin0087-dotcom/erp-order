import socket
import threading
import sys

def proxy_traffic(source_conn, target_host, target_port):
    try:
        with socket.create_connection((target_host, target_port)) as target_conn:
            def forward(src, dst):
                try:
                    while True:
                        data = src.recv(4096)
                        if not data: break
                        dst.sendall(data)
                except: pass

            t1 = threading.Thread(target=forward, args=(source_conn, target_conn))
            t2 = threading.Thread(target=forward, args=(target_conn, source_conn))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
    except Exception as e:
        print(f"Proxy error: {e}")
    finally:
        source_conn.close()

def start_proxy(listen_port, target_host, target_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('0.0.0.0', listen_port))
        server_sock.listen(5)
        print(f"Proxy listening on 0.0.0.0:{listen_port} -> {target_host}:{target_port}")
        while True:
            client, addr = server_sock.accept()
            threading.Thread(target=proxy_traffic, args=(client, target_host, target_port)).start()

if __name__ == "__main__":
    # Relay Windows 8080 to WSL 18789
    # Use 127.0.0.1 as WSL host (mapped by WSL2)
    start_proxy(8080, '127.0.0.1', 18789)
