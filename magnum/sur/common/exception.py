'''
Created on Aug 8, 2015

'''


class BaseException(Exception):

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message


class IdentityArgsError(BaseException):
    pass


class InvalidYAMLFileError(BaseException):
    pass


class HTTPException(BaseException):
    pass
