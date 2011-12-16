import socket
import logging

from common import Connection, BaseServerd


__all__     = ['EchoNode']
NEWLINE     = '\n'
log         = logging.getLogger('asynode')

class EchoIncoming(Connection):
    TERMINATOR = NEWLINE
    def collect_incoming_data(self, data):
        Connection.collect_incoming_data(self, data)
        self._buffer.append(data)

    def callback(self, data):
        Connection.callback(self, data)
        self._buffer = []

    def _close(self):
        self.close()


class EchoOutcoming(Connection):
    TERMINATOR = NEWLINE
    def sendit(self, host, port, *args):
        self._buffer = map(str,args)
        self.connect((host, port))

    def handle_connect(self):
        self._process(self._buffer, self.callback)

    def _close(self):
        self.push('')


class EchoNode(object):
    def __init__(self, incoming=None, outcoming=None):
        self.incoming = incoming or EchoIncoming
        self.outcoming = outcoming or EchoOutcoming

    def listen(self, host, port):
        BaseServerd(host, port, self.accept)

    def accept(self, sock):
        self.incoming(self.process_data, sock)

    def send(self, host, port, *args):
        self.outcoming(self.process_message).sendit(host, port, *args)
        
    @staticmethod
    def process_message(msg, callback):
        callback(msg.pop(0))

    @staticmethod
    def process_data(data, callback):
        callback(''.join(data))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from opt import input
    options, args = input()
    import asyncore
    node = EchoNode()
    if options.server:
        node.listen(options.host, options.port)
    else:
        node.send(options.host, options.port, *args)
        node.send(options.host, options.port, *args)
        node.send(options.host, options.port, *args)
    asyncore.loop()