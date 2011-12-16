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
    TERMINATOR = NotImplemented
    def __init__(self, callback, sock=None):
        sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asynchat.async_chat.__init__(self, sock)
        self._process = callback
        self.set_terminator(self.TERMINATOR)
        self._buffer = []
        if self.addr:
            log.info('Incoming connection from {a}'.format(a=self.addr))

    def push(self, msg):
        asynchat.async_chat.push(self, msg + self.TERMINATOR)

    def callback(self, data):
        if data:
            log.info('{l} => {r}: {d!r}'.format(l=self.socket.getsockname(), r=self.socket.getpeername(), d=data))
            self.push(data)

    def collect_incoming_data(self, data):
        log.info('{l} <= {r}: {d!r}'.format(l=self.socket.getsockname(), r=self.socket.getpeername(), d=data))

    def found_terminator(self):
        if not self._buffer:
            log.info('Closing {a}'.format(a=self.socket.getpeername()))
            self._close()
        self._process(self._buffer, self.callback)

    def handle_error(self):
        self._close()