import asyncore
import asynchat
import socket
import logging
log = logging.getLogger('asynode')

class BaseServerd(asyncore.dispatcher):
    def __init__ (self, host, port, on_accept):
        asyncore.dispatcher.__init__ (self)
        self.on_accept = on_accept
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        log.info('Listening on {h}:{p}'.format(h=host, p=port))

    def handle_accept(self):
        sock, _ = self.accept()
        self.on_accept(sock)


class Connection(asynchat.async_chat):
    TERMINATOR = '\n'
    def __init__(self, cid, callback, sock=None):
        sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asynchat.async_chat.__init__(self, sock)
        self.cid = cid
        self._process = callback
        self.set_terminator(self.TERMINATOR)
        self._buffer = []
        if self.addr:
            log.info('Incoming connection from {a}'.format(a=self.addr))

    def callback(self, data):
        if data is not None:
            log.info('{l} => {r}: {d!r}'.format(l=self.local, r=self.remote, d=data or '<QUIT>'))
            self.push(data)
            self.push(self.TERMINATOR)

    def collect_incoming_data(self, data):
        log.info('{l} <= {r}: {d!r}'.format(l=self.local, r=self.remote, d=data))
        self._buffer.append(data)

    def handle_connect(self):
        self._process(self._buffer, self.cid, self.callback)

    def found_terminator(self):
        if not self._buffer:
            log.info('Closing {a}'.format(a=self.addr))
            self.close()
        self._process(self._buffer, self.cid, self.callback)
        self._buffer = []

    @property
    def remote(self):
        return self.socket.getpeername()

    @property
    def local(self):
        return self.socket.getsockname()