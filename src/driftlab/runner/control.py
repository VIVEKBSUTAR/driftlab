"""Cooperative execution control, checked between inference requests."""


class RunCancelled(RuntimeError):
    pass


class WorkerStopping(RuntimeError):
    pass
