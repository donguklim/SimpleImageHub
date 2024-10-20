from fastapi.security import HTTPBearer
from fastapi import HTTPException, status
from starlette.requests import Request


class UnauthorizedException(HTTPException):
    def __init__(self, detail):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class TokenAuthScheme(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            raise UnauthorizedException(detail='Unauthorized user cannot access')

        token_type, token = auth_header.split(' ')

        if token_type != 'Bearer':
            raise UnauthorizedException(detail='Invalid token type')

        return token
