import logging
log         = logging.getLogger('asynode')

from common import Connection, BaseServerd
__all__     = ['EchoNode']

class FinalState(Exception):
    @property
    def final(self):
        return self.args[0]

class EchoOutcomingState(object):
    def __init__(self, *args):
        self._data = list(args)
        self._data.append('')

    def next(self, data):
        '''
        >>> s = EchoOutcomingState('a', 'b')
        >>> s._data
        ['a', 'b']
        >>> s.next('')
        'a'
        >>> s.next('')
        'b'
        >>> s.next('')
        Traceback (most recent call last):
            ...
        FinalState
        '''
        try:
            return self._data.pop(0)
        except IndexError:
            raise FinalState('')

class EchoIncomingState(object):
    def next(self, data):
        if ''.join(data):
            return ''.join(data)
        else:
            raise FinalState(None)


class EchoNode(object):
    def __init__(self, incoming=None, outcoming=None):
        self.incoming = incoming or Connection
        self.outcoming = outcoming or Connection
        self._id = 0
        self._cache = {}

    def listen(self, host, port):
        BaseServerd(host, port, self.accept)

    def accept(self, sock):
        cid = self.next_id
        self.incoming(cid, self.process, sock)
        self._cache[cid] = EchoIncomingState()

    def send(self, host, port, *args):
        cid = self.next_id
        self.outcoming(cid, self.process).connect((host, port))
        args = list(args)
        self._cache[cid] = EchoOutcomingState(*args)

    def process(self, data, cid, callback):
        try:
            next = self._cache[cid].next(data)
        except FinalState as e:
            del self._cache[cid]

            next = e.final
        callback(next)

    @property
    def next_id(self):
        self._id += 1
        return self._id


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
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()