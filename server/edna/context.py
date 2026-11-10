class RuntimeContext:
    """Explicit dependency context; legacy entrypoint overrides remain compatible."""
    def __init__(self,namespace):self._namespace=namespace
    def __getattr__(self,name):
        try:return self._namespace[name]
        except KeyError:raise AttributeError(name) from None
