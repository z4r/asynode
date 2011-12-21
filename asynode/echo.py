from common import ConnectionFactory
from state import State, Automaton

class EchoOutcomingAutomaton(Automaton):
    def __init__(self, *args):
        self._data = list(args)
        super(EchoOutcomingAutomaton, self).__init__()

    def initial(self, data):
        return State.get_push(terminator='\n')

    def operative(self, data):
        try:
            return State.get_push(push=self._data.pop(0)+'\n')
        except IndexError:
            return State.get_final(push='\n')


class EchoIncomingAutomaton(Automaton):
    def initial(self, data):
        return State.get_push(terminator='\n')

    def operative(self, data):
        if data:
            return State.get_push(push=data+'\n')
        else:
            return State.get_final()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    from opt import parse_input, main_loop
    OPTIONS, ARGS = parse_input()
    NODE = ConnectionFactory(
        instate=EchoIncomingAutomaton, outstate=EchoOutcomingAutomaton
    )
    if OPTIONS.server:
        NODE.listen(OPTIONS.host, OPTIONS.port)
    else:
        NODE.send(OPTIONS.host, OPTIONS.port, *ARGS)
    main_loop()
