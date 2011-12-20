from common import Node
from state import PushState, FinalState, IncomingAutomaton, OutcomingAutomaton

class EchoOutcomingAutomaton(OutcomingAutomaton):
    def __init__(self, *args):
        self._data = list(args)

    def INIT(self, data):
        return PushState(terminator='\n')

    def CONNECT(self, data):
        return self.TERMINATOR(data)

    def TERMINATOR(self, data):
        try:
            return PushState(push=self._data.pop(0)+'\n')
        except IndexError:
            return FinalState(push='\n')


class EchoIncomingAutomaton(IncomingAutomaton):
    def INIT(self, data):
        return PushState(terminator='\n')

    def TERMINATOR(self, data):
        if data:
            return PushState(push=data+'\n')
        else:
            return FinalState()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    from opt import input
    options, args = input()
    import asyncore
    node = Node(instate=EchoIncomingAutomaton, outstate=EchoOutcomingAutomaton)
    if options.server:
        node.listen(options.host, options.port)
    else:
        node.send(options.host, options.port, *args)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()