import typing

from django.contrib.sessions.backends.base import SessionBase
from allauth.headless.tokens.base import AbstractTokenStrategy
from rest_framework_simplejwt.tokens import AccessToken
from allauth.headless.internal import sessionkit


class SessionTokenStrategy(AbstractTokenStrategy):
    def create_session_token(self, request) -> str | None:
            user = request.user
            if user.is_authenticated:
                # Generate a JWT access token for the authenticated user
                token = AccessToken.for_user(user)
                return str(token)
            return None

    def lookup_session(self, session_token: str) -> typing.Optional[SessionBase]:
        session_key = session_token
        if sessionkit.session_store().exists(session_key):
            return sessionkit.session_store(session_key)
        return None
