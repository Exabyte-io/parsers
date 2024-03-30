from mat3ra.parsers import BaseParser


class EspressoPwxStdinParser(BaseParser):
    """
    Espresso PWX stdin parser class.
    """

    def __init__(self, content, version: str = None):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)
