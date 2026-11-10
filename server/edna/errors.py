class HTTPError(Exception):

    def __init__(self, code, message):
        self.code, self.message = (code, message)

def require(cond, message, code=400):
    if not cond:
        raise HTTPError(code, message)
