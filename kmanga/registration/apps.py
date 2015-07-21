from django.apps import AppConfig


class RegistrationConfig(AppConfig):
    name = 'registration'
    verbose_name = 'User Registration'

    def ready(self):
        from . import signals
