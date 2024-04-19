from mat3ra.parsers import BaseParser
from pymatgen.core.structure import Structure


class VASPStdinParser(BaseParser):

    def __init__(self, content, version: str = "5.3.5"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)
        self.structure = Structure.from_str(self.content, "poscar")
