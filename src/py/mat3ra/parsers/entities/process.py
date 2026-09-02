from mat3ra.parsers import BaseParser
from mat3ra.parsers.factory import ParserFactory


class ProcessParser(BaseParser):
    """
    Process parser class: turns a fabrication record from a laboratory system into an ESSE
    process config, the experimental counterpart of MaterialParser.

    Args:
        args (list): args passed to the parser.
        kwargs (dict): kwargs passed to the parser.
            content (str): record content.
            format (str): record format, e.g. applications.lmc.deposition.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def pre_parser(self):
        parser_name = self.format
        return ParserFactory.get_class_by_name(parser_name)(self.content, version=self.version)

    def _serialize(self):
        """
        Serialize a process.

        Returns:
             dict
        """
        return self.pre_parser.to_dict()
