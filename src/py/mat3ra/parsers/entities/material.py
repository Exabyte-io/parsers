from mat3ra.parsers import BaseParser
from mat3ra.parsers.factory import ParserFactory


class MaterialParser(BaseParser):
    """
    Structure parser class.

    Args:
        args (list): args passed to the parser.
        kwargs (dict): kwargs passed to the parser.
            structure_string (str): structure string.
            structure_format (str): structure format, poscar or espresso-in.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def pre_parser(self):
        parser_name = self.format
        return ParserFactory.get_class_by_name(parser_name)(self.content, version=self.version)

    @property
    def basis(self):
        return self.pre_parser.basis

    @property
    def formula(self):
        return self.pre_parser.formula

    @property
    def lattice(self):
        return self.pre_parser.lattice

    @property
    def name(self):
        return self.pre_parser.name

    def _serialize(self):
        """
        Serialize a material.

        Returns:
             dict
        """
        return {
            "_id": "",
            "name": self.name,
            "exabyteId": "",
            "hash": "",
            "formula": self.formula,
            "unitCellFormula": self.unitCellFormula,
            "lattice": self.lattice,
            "basis": self.basis,
            "derivedProperties": self.derived_properties,
            "creator": {"_id": "", "cls": "User", "slug": ""},
            "owner": {"_id": "", "cls": "Account", "slug": ""},
            "schemaVersion": "0.2.0",
        }
