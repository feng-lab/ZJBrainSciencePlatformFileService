from typing import Awaitable, Callable, TypeAlias

from fastapi import Request, Response

MiddlewareCallNext: TypeAlias = Callable[[Request], Awaitable[Response]]
