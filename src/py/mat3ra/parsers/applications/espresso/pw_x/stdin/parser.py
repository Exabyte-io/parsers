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

    def parse(self):
        """
        Parse the content.

        Returns:
            dict
        """
        return {
            "content": self.content,
            "version": self.version,
        }

    def to_dict(self):
        """
        Returns a dictionary representation of the parser.

        Returns:
            dict
        """
        return {
            "content": self.content,
            "version": self.version,
        }

    def to_json(self):
        """
        Returns a JSON representation of the parser.

        Returns:
            str
        """
        return str(self.to_dict())
