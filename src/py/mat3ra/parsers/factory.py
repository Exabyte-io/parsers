from mat3ra.utils import factory as factory


class ParserFactory(factory.BaseFactory):
    """
    Parser Factory class.
    """

    __class_registry__ = {
        "applications.espresso.pw_x.stdin": "mat3ra.parsers.applications.espresso.stdin.EspressoPWXStdinParser",
        "applications.vasp.stdin": "mat3ra.parsers.applications.vasp.VASPStdinParser",
    }
