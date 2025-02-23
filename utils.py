import enum
import functools
import re

from auth0 import Auth0Error
from auth0.authentication import GetToken, Database, Users
from fastapi import HTTPException, status

from config import get_settings


class UnauthenticatedException(HTTPException):
    pass


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        super().__init__(status.HTTP_403_FORBIDDEN, detail=detail)


def authorized_only(func):
    from schema import ErrorResponse
    from context import NoTokenException

    @functools.wraps(func)
    def wrapper(self, info, *args, **kwargs):
        try:
            user = info.context.user
        except Auth0Error as e:
            return ErrorResponse(error=repr(e))
        except NoTokenException as e:
            return ErrorResponse(error=str(e))
        if not user:
            return ErrorResponse(error="Can't find user with given credentials")
        return func(self, info, *args, **kwargs)
    return wrapper


class HandleToken:
    def __init__(self):
        self.config = get_settings()
        self.admin_credentials = {
            'domain': self.config.domain,
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret}
        self.jwks_url = f"https://{self.config.domain}/.well-known/jwks.json"

    def sign_up(self, email, password):
        user_db = Database(**self.admin_credentials)
        user = user_db.signup(
            email, password, "Username-Password-Authentication")
        return user

    def sign_in(self, email, password):
        token_client = GetToken(**self.admin_credentials)
        token_response = token_client.login(
            email, password,
            realm='Username-Password-Authentication',
            audience=self.config.api_audience,
            scope=self.config.scopes)
        return token_response

    def get_user_info(self, token):
        users_service = Users(self.config.domain)
        return users_service.userinfo(token)


oauth_handler = HandleToken()


class Language(enum.Enum):
    RUS = 'rus'
    GREEK = 'greek'
    OTHER = 'other'


LANG_MAPPING = {
    Language.RUS: re.compile(r"^[а-яё]+$", re.IGNORECASE),
    Language.GREEK: re.compile(r"^[α-ωάέήίόύώ]+$", re.IGNORECASE)
}


def detect_language(text: str) -> Language:
    for lang, pattern in LANG_MAPPING.items():
        if pattern.match(text):
            return lang
    return Language.OTHER
