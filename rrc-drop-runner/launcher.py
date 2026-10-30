"""Windows desktop entry point: one loopback server, bundled runtimes, browser UI."""
import json
import logging
import os
import socket
from pathlib import Path
import sys
import time
import urllib.request
import webbrowser

DATA = Path(os.environ.get('RRC_DATA_DIR', str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Texas RRC Data Converter')))

def show_error(message):
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'Data Train', 0x10)
    else: print(message, file=sys.stderr)

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=DATA/'application.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    instance = DATA/'instance.json'
    lock = open(DATA/'application.lock', 'a+b')
    # Do not read byte zero: another Windows instance may already hold its byte
    # lock, and even a read would fail before the nonblocking lock attempt.
    if os.fstat(lock.fileno()).st_size == 0: lock.write(b'0'); lock.flush()
    lock.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        for _ in range(100):
            try:
                info = json.loads(instance.read_text())
                with urllib.request.urlopen(info['url']+'api/health', timeout=.5) as response:
                    health = json.load(response)
                if health.get('application') == 'Data Train' and health.get('pid') == info['pid']:
                    if os.environ.get('RRC_NO_BROWSER') != '1': webbrowser.open(info['url'])
                    logging.info('Reopened existing application at %s',info['url'])
                    return
            except Exception: time.sleep(.05)
        show_error('The application is already starting. Wait a moment, then double-click it again.')
        return
    try:
        from app import app
        from service import cleanup
        from waitress import create_server, wasyncore
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Waitress otherwise enables SO_REUSEADDR, which can share a Windows port
        # with an unrelated listener. Reserve an exclusive socket before serving.
        if os.name == 'nt': listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try: listener.bind(('127.0.0.1',5055))
        except OSError: listener.bind(('127.0.0.1',0))
        server = create_server(app, sockets=[listener], max_request_body_size=20*1024**3, threads=4)
        url = 'http://127.0.0.1:'+str(server.effective_port)+'/'
        instance.write_text(json.dumps(dict(pid=os.getpid(), url=url)), encoding='utf-8')
        def stop():
            server.task_dispatcher.shutdown(timeout=5)
            wasyncore.close_all(map=server._map)
        app.config['RRC_SHUTDOWN'] = stop
        if os.environ.get('RRC_NO_BROWSER') != '1': webbrowser.open(url)
        logging.info('Application listening at %s',url)
        try: server.run()
        finally:
            stop()
            cleanup()
            instance.unlink(missing_ok=True)
            logging.info('Application stopped')
    except Exception:
        logging.exception('Application startup failed')
        show_error('The application could not start. Extract the complete ZIP to a folder you can access and try again. Details: '+str(DATA/'application.log'))
    finally: lock.close()

if __name__ == '__main__': main()
