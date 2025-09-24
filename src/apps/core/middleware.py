from django.db.models import signals
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user
from rest_framework.request import Request
from functools import partial as curry


class AuthenticationMiddlewareJWT(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: self.__class__.get_jwt_user(request))
        return self.get_response(request)

    @staticmethod
    def get_jwt_user(request):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        user = get_user(request)
        if user.is_authenticated:
            return user
        try:
            user_jwt = JWTAuthentication().authenticate(Request(request))
            if user_jwt is not None:
                return user_jwt[0]
        except:
            pass
        return user # AnonymousUser


class WhodidMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
            else:
                user = None

            mark_whodid = curry(self.mark_whodid, user)
            signals.pre_save.connect(
                mark_whodid,
                dispatch_uid=(self.__class__, request,),
                weak=False)

        response = self.get_response(request)

        signals.pre_save.disconnect(dispatch_uid=(self.__class__, request,))

        return response

    def mark_whodid(self, user, sender, instance, **kwargs):
        if not getattr(instance, 'created_by_id', None):
            instance.created_by = user
        if hasattr(instance, 'modified_by_id'):
            instance.modified_by = user
