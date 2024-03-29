from mat3ra.utils import mixins
from mat3ra.utils import file as utils


class BaseParser(mixins.RoundNumericValuesMixin):
    """
    Base Parser class.
    """

    def __init__(self, content, format: str = None, version: str = None):
        self.content = content
        self.format = format
        self.version = version

    @staticmethod
    def from_file(file_path: str, format: str = None, version: str = None):
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
