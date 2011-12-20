from collections import namedtuple

__all__ = (
    'State',
    'PushState',
    'PassState',
    'FinalState',
    'IncomingAutomaton',
    'OutcomingAutomaton',
)

State = namedtuple('State', ('push', 'terminator', 'close', 'final'))

def PassState():
    return State(None, None, False, False)

def PushState(push=None, terminator=None):
    return State(push, terminator, False, False)

def FinalState(push=None, close=False):
    return State(push, None, close, True)

class Automaton(object):
    def __init__(self, *args, **kwargs):
        pass

    def next(self, data, state='TERMINATOR'):
        return getattr(self, state.lower())(data)

    def initial(self, data):
        raise NotImplementedError

    def terminator(self, data):
        raise NotImplementedError


class IncomingAutomaton(Automaton):
    pass


class OutcomingAutomaton(Automaton):
    def connect(self, data):
        raise NotImplementedError