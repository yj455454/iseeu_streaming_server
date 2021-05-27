from socket import *
from threading import Thread
from mysite.net import NetFile
from queue import Queue
import json

# HOST = 'localhost'
HOST = '192.168.0.41'
PORT = 6000
STREAM_PORT = 6001

class Proxy(NetFile):
    def __init__(self, id, dtype, c_socket):
        super().__init__(c_socket)
        self.id = id
        self.dtype = dtype

    def ping(self):
        self.send_json({'cmd': 'ping'})
        pong = self.readline()
        print(f'{self.id} ', pong)

    def command(self, cmd, kwargs = {}):
        try:
            self.send_json({'cmd': cmd, 'kwargs': kwargs})
            return True
        except:
            print(f'{cmd} 전송 실패')
            pool.reave(self.id)
            return False


class CameraProxy(Proxy, Thread):   # Camera Subject
    def __init__(self, id, dtype, c_socket):
        Thread.__init__(self)
        Proxy.__init__(self, id, dtype, c_socket)

        global STREAM_PORT
        STREAM_PORT += 1
        
        self.port = STREAM_PORT
        self.setDaemon(True)
        self.queue = Queue()
        self.observers = []
        self.start()
        
    def regist(self, ob):
        self.observers.append(ob)
        if len(self.observers) == 1:
            self.command("start_stream", kwargs = {"host": HOST, "port": self.port})

    def unregist(self, ob):
        self.observers.remove(ob)
        if not self.observers:
            self.command("stop_stream")

    def notify_all(self, data):
        for ob in self.observers:
            ob.update(data)

    def run(self):
        # STREAM은 UDP 통신으로 처리
        with socket(type= SOCK_DGRAM) as s:
            try:
                s.bind((HOST, self.port))
                while True:
                    # 패킷의 크기 주의
                    data, addr = s.recvfrom(150000)
                    self.notify_all(data)
            except Exception as e:
                print(e)
                print('send stop_stream')
                self.command('stop_stream')


class MjpegObserver:
    def __init__(self, subject):
        self.queue = Queue(1)
        self.subject = subject

    def update(self, data):
        if self.queue.empty():
            self.queue.put(data)

    def mjpeg(self):        
        print('regist')
        self.subject.regist(self)
        try:
            while True:
                data = self.queue.get()
                # yield (b'--frame\r\n'
                #         b'Content-Length: ' + f'{len(data)}'.encode() + b'\r\n'
                #         b'Content-Type: image/jpeg\cr\n\r\n' + data + b'\r\n')

                yield (b'--myboundary\n'
                    b'Content-Type::image/jpeg\n'
                    b'Content-Length: ' + f"{len(data)}".encode() + b'\n'
                    b'\n' + data + b'\n')

        finally :
            print('unregist')
            self.subject.unregist(self)


def create_proxy(c_socket):
    buf = c_socket.recv(1024)
    msg = json.loads(buf)
    device_id = msg.get('id')
    dtype = msg.get('dtype')

    if dtype == 'CAMERA':
        proxy = CameraProxy(device_id, dtype, c_socket)
    else:
        proxy = Proxy(device_id, dtype, c_socket)

    pool.join(msg['id'], proxy)


class ProxyPool(Thread):
    def __init__(self):
        super().__init__()
        self.setDaemon(True)
        self.pool = {}

    def join(self, id, proxy):
        self.pool[id] = proxy
        print('device join', id)

    def leave(self, id):
        self.pool[id] = None
        print('device leave', id)

    def get(self, id):        
        proxy = self.pool.get(id)
        if proxy:
            try: # 접속 유지 상태인지 확인
                proxy.ping()    
                return proxy
            except:
                self.leave(proxy.id)
        else:
            print('pool에 등록되지 않음', id)
        return None

    def run(self):
        with socket() as s:
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.settimeout(1)   
            s.bind((HOST, PORT))
            s.listen(1)     
            while True:
                try:
                    client_socket, _ = s.accept()	
                    Thread(target= create_proxy, args=(client_socket,)).start()
                except Exception as e:
                    if e.__class__.__name__ == 'timeout': pass
                    else: print(e)
                    
pool = ProxyPool()
pool.start()


