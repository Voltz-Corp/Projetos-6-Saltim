from .session_memory import clear_session_state


def perguntar(*args, **kwargs):
    from .agent import perguntar as _perguntar

    return _perguntar(*args, **kwargs)


def call_agent(*args, **kwargs):
    from .agent import call_agent as _call_agent

    return _call_agent(*args, **kwargs)


__all__ = ["call_agent", "perguntar", "clear_session_state"]
