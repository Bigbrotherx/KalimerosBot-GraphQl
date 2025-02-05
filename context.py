from dataclasses import dataclass
from functools import cached_property

from strawberry.fastapi import BaseContext

from utils import oauth_handler


class NoTokenException(Exception):
    pass


@dataclass
class User:
    id: str
    name: str
    email: str


class Context(BaseContext):
    @cached_property
    def user(self) -> User | None:
        token = self.request.headers.get(
            'Authorization', '').replace('Bearer ', '')
        if token == '':
            raise NoTokenException('Please provide a valid token')
        user_data = oauth_handler.get_user_info(token)
        user = User(id=user_data['sub'].split('|')[1],
                    name=user_data['name'],
                    email=user_data['email'])
        return user


async def get_context() -> Context:
    return Context()
