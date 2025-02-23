from collections import defaultdict
from typing import Union, Annotated
from fastapi import status

import strawberry
from auth0 import Auth0Error
from strawberry import Info

from context import Context, User
from utils import oauth_handler, authorized_only, detect_language, Language
from config import get_settings, get_dictionary_service_channel
from protobuf import dictionary_service_pb2, dictionary_service_pb2_grpc

SETTINGS = get_settings()

rus_to_greek = {
    "привет": "γεια",
    "мир": "κόσμος",
    "кот": "γάτα",
}

greek_to_rus = {
    "γεια": "привет",
    "κόσμος": "мир",
    "γάτα": "кот",
}

user_progress = {}


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


@strawberry.type
class TrainingSession:
    word: str
    completed: int
    total: int


StandardResponse = Annotated[
    Union[SuccessResponse, ErrorResponse],
    strawberry.union("StandardResponse")]

LoginResult = Annotated[
    Union[AuthPayload, ErrorResponse], strawberry.union("LoginResult")
]

TrainingSessionResult = Annotated[
    Union[TrainingSession, ErrorResponse, SuccessResponse],
    strawberry.union("SubmitAnswerResult")]


# noinspection PyArgumentList
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello world"

    @strawberry.field
    def get_translation(self, word: str) -> StandardResponse:
        language = detect_language(word)
        if language == Language.OTHER:
            return ErrorResponse(
                error='Only Greek or Russian languages are supported')
        if language == Language.GREEK:
            translation = greek_to_rus.get(word)
            if translation:
                return SuccessResponse(message=translation)
            return ErrorResponse(error=f"Can't translate '{word}'")
        else:
            translation = rus_to_greek.get(word)
            if translation:
                return SuccessResponse(message=translation)
            return ErrorResponse(error=f"Can't translate '{word}'")

    @strawberry.field
    def get_random_translation(self) -> str:
        return "Random Translation"

    @strawberry.field
    @authorized_only
    def start_training(self, info: Info[Context]) -> TrainingSessionResult:
        total = len(greek_to_rus)
        user_progress[info.context.user.id] = {"completed": 0,
                                               "total": total}
        first_word = next(iter(greek_to_rus))
        return TrainingSession(
            word=first_word,
            completed=0,
            total=total
        )


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
            return ErrorResponse(
                error=e.message if e.message else e.error_code)
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
                 new_word: DictionaryInput) -> StandardResponse:
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

    @strawberry.mutation
    @authorized_only
    def submit_answer(
            self, info: Info[Context], answer: str) -> TrainingSessionResult:
        user_id = info.context.user.id
        if user_id not in user_progress:
            return ErrorResponse(
                error='Please start the training session first!')
        session = user_progress[user_id]

        if session["completed"] >= session["total"]:
            return SuccessResponse(message='You are all done!')

        if answer:
            session["completed"] += 1

        if session["completed"] >= session["total"]:
            return SuccessResponse(message='You are all done!')
        completed = session["completed"]
        return TrainingSession(
            word=list(greek_to_rus)[completed],
            completed=completed,
            total=session["total"],
        )

    @strawberry.mutation
    @authorized_only
    def stop_training(self, info: Info[Context]) -> StandardResponse:
        user_id = info.context.user.id
        if user_id in user_progress:
            del user_progress[user_id]  # Удаляем данные пользователя
            return SuccessResponse(message='Training session finished!')
        return ErrorResponse(error="You are didn't start the training yet!")


schema = strawberry.Schema(query=Query, mutation=Mutation)
