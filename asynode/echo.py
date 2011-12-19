import logging
log         = logging.getLogger('asynode')

from common import Node, FinalState

class EchoOutcomingState(object):
    def __init__(self, *args):
        self._data = list(args)

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
        '''
        >>> s = EchoIncomingState()
        >>> s.next(['a', 'b'])
        'ab'
        >>> s.next([''])
        Traceback (most recent call last):
            ...
        FinalState: None
        '''
        ret = ''.join(data)
        if ret:
            return ret
        else:
            raise FinalState(None)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    from opt import input
    options, args = input()
    import asyncore
    node = Node(instate=EchoIncomingState, outstate=EchoOutcomingState)
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