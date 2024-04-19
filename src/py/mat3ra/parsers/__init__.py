from mat3ra.utils import file as utils
from mat3ra.utils import mixins


class BaseParser(mixins.RoundNumericValuesMixin):
    """
    Base Parser class.
    """

    PRECISION_MAP = {
        # decimal places
        "coordinates_crystal": 9,
        "coordinates_cartesian": 6,
        "angles": 4,
    }

    def __init__(self, content, format: str = "", version: str = ""):
        self.content = content
        self.format = format
        self.version = version

    @staticmethod
    def from_file(file_path: str, format: str = "", version: str = ""):
        """
        Returns a parser instance from a file.

        Args:
            file_path (str): file path.
            format (str): file content format.
            version (str): file version.

        Returns:
            class
        """
        content = utils.get_file_content(file_path)
        return BaseParser(content, format=format, version=version)

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
