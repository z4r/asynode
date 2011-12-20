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
    def __init__(self, cid, callback, sock=None):
        sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asynchat.async_chat.__init__(self, sock)
        self.cid = cid
        self._process = callback
        self._buffer = []
        if self.addr:
            log.info('Incoming connection from {a}'.format(a=self.addr))
        self._process('INIT', self._buffer, cid, self.callback)

    def callback(self, data=None, terminator=None, close=False):
        log.debug('CALLBACK {d!r} {t!r}'.format(d=data, t=terminator))
        if terminator is not None:
            log.debug('Setting terminator to {t!r}'.format(t=terminator))
            self.set_terminator(terminator)
        if data is not None:
            log.info('{l} => {r}: {d!r}'.format(l=self.local, r=self.remote, d=data.strip() or '<QUIT>'))
            self.push(data)
        if close:
            self.close_when_done()

    def collect_incoming_data(self, data):
        log.info('{l} <= {r}: {d!r}'.format(l=self.local, r=self.remote, d=data))
        self._buffer.append(data)

    def handle_connect(self):
        log.info('Connected to {a}'.format(a=self.remote))
        self._process('CONNECT', self._buffer, self.cid, self.callback)

    def found_terminator(self):
        if not self._buffer:
            self.handle_close()
        self._process('TERMINATOR', self._buffer, self.cid, self.callback)
        self._buffer = []

    def handle_close(self):
        log.info('Closing {a}'.format(a=self.remote or ''))
        asynchat.async_chat.handle_close(self)

    @property
    def remote(self):
        return self.socket.getpeername()

    @property
    def local(self):
        return self.socket.getsockname()


class Node(object):
    def __init__(self, instate, outstate, listener=None, inconn=None, outconn=None):
        self.instate = instate
        self.outstate = outstate
        self.listener = listener or BaseServerd
        self.incoming = inconn or Connection
        self.outcoming = outconn or Connection
        self._id = 0
        self._cache = {}

    def listen(self, host, port):
        self.listener(host, port, self.accept)

    def accept(self, sock):
        cid = self.next_id
        self._cache[cid] = self.instate()
        self.incoming(cid, self.process, sock)

    def send(self, host, port, *args, **kwargs):
        cid = self.next_id
        self._cache[cid] = self.outstate(*args, **kwargs)
        self.outcoming(cid, self.process).connect((host, port))

    def process(self, state, data, cid, callback):
        next = self._cache[cid].next(''.join(data), state)
        if next.final:
            del self._cache[cid]
        callback(next.push, next.terminator, next.close)

    @property
    def next_id(self):
        self._id += 1
        return self._id