from typing import Union, Annotated
from fastapi import status

import strawberry
from auth0 import Auth0Error
from strawberry import Info

from context import Context, User
from utils import oauth_handler, authorized_only
from config import get_settings, get_dictionary_service_channel
from protobuf import dictionary_service_pb2, dictionary_service_pb2_grpc

SETTINGS = get_settings()


# noinspection PyArgumentList
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello world"


@strawberry.input
class DictionaryInput:
    word: str
    translation: str


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.type
class AuthPayload:
    access_token: str
    refresh_token: str
    expires_in: int


@strawberry.type
class ErrorResponse:
    error: str


@strawberry.type
class SuccessResponse:
    message: str


LoginResult = Annotated[
    Union[AuthPayload, ErrorResponse], strawberry.union("LoginResult")
]

AddWordResult = Annotated[
    Union[SuccessResponse, ErrorResponse], strawberry.union("AddWordResult")]


# noinspection PyArgumentList
@strawberry.type
class Mutation:

    @staticmethod
    def _generate_tokens(credentials: LoginInput) -> LoginResult:
        """Общая логика для получения токенов и их проверки."""
        try:
            token = oauth_handler.sign_in(
                credentials.email, credentials.password)
            if not token or oauth_handler.get_user_info(
                    token['access_token']) is None:
                return ErrorResponse(error='Invalid credentials')
            return AuthPayload(
                access_token=token["access_token"],
                refresh_token=token["refresh_token"],
                expires_in=token["expires_in"])
        except Auth0Error as e:
            return ErrorResponse(error=e.message)
        except Exception as e:
            return ErrorResponse(error=repr(e))

    @strawberry.mutation
    def sign_up(self, credentials: LoginInput) -> LoginResult:
        """Регистрация пользователя."""
        try:
            user = oauth_handler.sign_up(
                credentials.email, credentials.password)
            if not user:
                return ErrorResponse(error='Some error occurred')
        except Auth0Error as e:
            return ErrorResponse(error=e.message)
        except Exception as e:
            return ErrorResponse(error=repr(e))

        return Mutation._generate_tokens(credentials)

    @strawberry.mutation
    def sign_in(self, credentials: LoginInput) -> LoginResult:
        """Вход пользователя."""
        return Mutation._generate_tokens(credentials)

    @strawberry.mutation
    @authorized_only
    def add_word(self, info: Info[Context],
                 new_word: DictionaryInput) -> AddWordResult:
        with get_dictionary_service_channel() as channel:
            stub = dictionary_service_pb2_grpc.DictionaryServiceStub(channel)
            response = stub.AddWord(
                dictionary_service_pb2.AddWordRequest(
                    user_id=info.context.user.id,
                    word=new_word.word,
                    translation=new_word.translation))
            if response.status_code == status.HTTP_200_OK:
                return SuccessResponse(message=response.message)
        return ErrorResponse(error=response.message)


schema = strawberry.Schema(query=Query, mutation=Mutation)
