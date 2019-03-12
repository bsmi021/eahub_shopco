class NotFound(Exception):
    pass

class OrderingException(Exception):

    def __init__(self, message):
        self.message = message
