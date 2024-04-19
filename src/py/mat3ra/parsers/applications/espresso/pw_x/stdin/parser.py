import re
from mat3ra.parsers import BaseParser
from mat3ra.regex.data.schemas import SCHEMAS
from mat3ra.utils import object as object_utils
from mat3ra.utils import regex as regex_utils


class EspressoPwxStdinParser(BaseParser):
    """
    Espresso PWX stdin parser class.
    """

    schema_path = "/applications/espresso/5.2.1/pw.x/"

    def __init__(self, content, version: str = "5.4.0"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)
        self.namelist_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "control/_format/namelist"
        )
        self.namelist_regex = self.namelist_regex_object["regex"]
        self.namelist_flags = self.namelist_regex_object["flags"]
        self.namelist_regex_control = self.namelist_regex.replace("{{BLOCK_NAME}}", "CONTROL")
        self.namelist_regex_electrons = self.namelist_regex.replace("{{BLOCK_NAME}}", "ELECTRONS")

    @staticmethod
    def get_value_from_namelist_by_key(namelist_content: str, namelist_name: str, key: str):
        regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + f"{namelist_name}/{key}"
        )
        regex = re.compile(
            regex_object["regex"],
            regex_utils.convert_js_flags_to_python(regex_object["flags"]),
        )
        matches = list(regex.finditer(namelist_content))
        line, value = (None, None)
        if len(matches) > 0:
            line, value = matches[0].group(0), matches[0].group(1)
        return line, value

    @property
    def namelist_control(self):
        control_block_regex = re.compile(
            self.namelist_regex_control.encode().decode("unicode_escape"),
            regex_utils.convert_js_flags_to_python(self.namelist_flags),
        )
        control_blocks_match = control_block_regex.match(self.content)
        control_block = control_blocks_match[0] if control_blocks_match else None

        _ = lambda x: self.get_value_from_namelist_by_key(control_block, "control", x)[1]

        return {
            "calculation": _("calculation"),
            "title": _("title"),
            "restart_mode": _("restart_mode"),
        }
