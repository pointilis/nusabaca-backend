import typing

from typing import Any, Dict, Optional
from django.http import HttpRequest
from django.contrib.sessions.backends.base import SessionBase
from allauth.headless.tokens.base import AbstractTokenStrategy
from rest_framework_simplejwt.tokens import AccessToken
from allauth.headless.internal import sessionkit


class SessionTokenStrategy(AbstractTokenStrategy):
    def create_session_token(self, request: HttpRequest) -> str:
        if not request.session.session_key:
            request.session.save()
        key = request.session.session_key
        # We did save
        assert isinstance(key, str)  # nosec
        return key

    def create_jwt_token(self, request) -> str | None:
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

    def create_access_token_payload(
        self, request: HttpRequest
    ) -> Optional[Dict[str, Any]]:
        """
        After authenticating, this method is called to create the access
        token response payload, exposing the access token and possibly other
        information such as a ``refresh_token`` and ``expires_in``.
        """
        at = self.create_access_token(request)
        jwt = self.create_jwt_token(request)
        if not jwt:
            jwt = None

        if not at:
            return None
        return {"access_token": at, "jwt_token": jwt}
