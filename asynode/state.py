from collections import namedtuple

__all__ = (
    'State',
    'Automaton',
)

class State(namedtuple('State', ('push', 'terminator', 'close', 'final'))):
    @classmethod
    def get_push(cls, push=None, terminator=None):
        return cls(push, terminator, False, False)

    @classmethod
    def get_final(cls, push=None, close=False):
        return cls(push, None, close, True)

class Automaton(object):
    def next(self, data, state='OPERATIVE'):
        return getattr(self, state.lower())(data)

    def initial(self, data):
        raise NotImplementedError

    def operative(self, data):
        raise NotImplementedError

    def error(self, data):
        raise NotImplementedError
