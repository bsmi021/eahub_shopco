class BaseConfig:
    """ Base Configuration"""
    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    """ Dev configuratino"""
    DEBUG = True


class TestingConfig(BaseConfig):
    """ Testing config"""
    DEBUG = True
    TESTING = True


class ProductionConfig(BaseConfig):
    """ Production Config """
    DEBUG = False
