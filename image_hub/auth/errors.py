class AuthTokenError(Exception):
    pass


class ExpiredToken(AuthTokenError):
    def __init__(self):
        super().__init__('JWT token has expired')


class InvalidToken(AuthTokenError):
    def __init__(self, token):
        super().__init__(f'Invalid JWT token: {token}')


class InvalidDecodedToken(AuthTokenError):
    def __init__(self, message):
        super().__init__(message)
