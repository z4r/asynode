from common import ConnectionFactory
from state import PushState, FinalState, IncomingAutomaton, OutcomingAutomaton

class EchoOutcomingAutomaton(OutcomingAutomaton):
    def __init__(self, *args):
        self._data = list(args)
        super(EchoOutcomingAutomaton, self).__init__()

    def initial(self, data):
        return PushState(terminator='\n')

    def connect(self, data):
        return self.terminator(data)

    def terminator(self, data):
        try:
            return PushState(push=self._data.pop(0)+'\n')
        except IndexError:
            return FinalState(push='\n')


class EchoIncomingAutomaton(IncomingAutomaton):
    def initial(self, data):
        return PushState(terminator='\n')

    def terminator(self, data):
        if data:
            return PushState(push=data+'\n')
        else:
            return FinalState()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    from opt import parse_input
    OPTIONS, ARGS = parse_input()
    import asyncore
    NODE = ConnectionFactory(
        instate=EchoIncomingAutomaton, outstate=EchoOutcomingAutomaton
    )
    if OPTIONS.server:
        NODE.listen(OPTIONS.host, OPTIONS.port)
    else:
        NODE.send(OPTIONS.host, OPTIONS.port, *ARGS) # pylint: disable=W0142
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()