from typing import List, Optional

from mat3ra.parsers import BaseParser
from mat3ra.regex.data.schemas import SCHEMAS
from mat3ra.utils import object as object_utils
from mat3ra.utils import regex as regex_utils
from mat3ra.utils.constants import COEFFICIENTS
from mat3ra.parsers.utils import cast_fortran_string


class EspressoPwxStdinParser(BaseParser):
    """
    Espresso PWX stdin parser class.
    """

    schema_path = "/applications/espresso/5.2.1/pw.x/stdin"

    def __init__(self, content, version: str = "5.4.0"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): Quantum ESPRESSO version.
        """
        super().__init__(content, version=version)
        self.stdin_schema = object_utils.get(SCHEMAS, self.schema_path) or {}
        self.partials_schema = object_utils.get(SCHEMAS, "/applications/espresso/partials") or {}

    def get_namelist(self, namelist_name: str) -> dict:
        """
        Extracts an entire namelist block and parses all key=value pairs into a dictionary.
        This handles standard keys and Fortran indexed arrays like celldm(N) or starting_magnetization(N).
        """
        namelist_schema = self.stdin_schema.get(namelist_name.lower(), {}).get("_format")

        matches = list(regex_utils.regex_search_by_schema(content=self.content, schema=namelist_schema, find_all=True))

        if not matches:
            return {}

        block_content = matches[0].group(0)
        result = {}

        for kv_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair"), find_all=True
        ):
            k = kv_match.group(1).strip().lower()
            v = kv_match.group(2).strip().strip("'\"")
            result[k] = cast_fortran_string(v)

        for array_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair_with_index"), find_all=True
        ):
            key = array_match.group(1).strip().lower()
            index = array_match.group(2).strip()
            value = array_match.group(3).strip().strip("'\"")
            result[f"{key}{index}"] = cast_fortran_string(value)

        return result

    @property
    def celldm1_angstrom(self) -> Optional[float]:
        """
        Helper property to extract celldm(1) from the SYSTEM namelist and convert it to Angstroms.
        """
        system_nl = self.get_namelist("system")
        celldm1_bohr = system_nl.get("celldm1")
        return float(celldm1_bohr) * COEFFICIENTS["BOHR_TO_ANGSTROM"] if celldm1_bohr else None

    def get_card_cell_parameters(self) -> Optional[List[List[float]]]:
        """
        Parses the CELL_PARAMETERS card and converts coordinates to Cartesian Angstroms.
        """
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.stdin_schema.get("cell_parameters_card")
        )

        if not match:
            return None

        units = match.group(1).lower() if match.group(1) else "alat"
        rows = []
        for row_match in regex_utils.regex_search_by_schema(
            content=match.group(2),
            schema=self.partials_schema.get("cell_parameters_row"),
            find_all=True,
        ):
            row = row_match.groupdict()
            rows.append([float(row[c]) for c in ("x", "y", "z")])

        return {
            "card_option": units,
            "values": {
                "v1": rows[0],
                "v2": rows[1],
                "v3": rows[2]
            }
        }

    def get_card_atomic_positions(self) -> Optional[dict]:
        """
        Parses the ATOMIC_POSITIONS card and converts coordinates to Cartesian Angstroms.
        """
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.stdin_schema.get("atomic_positions_card")
        )
        if not match:
            return None

        units = match.group(1).lower() if match.group(1) else "alat"
        values = []

        for row_match in regex_utils.regex_search_by_schema(
            content=match.group(2),
            schema=self.partials_schema.get("atomic_positions_row"),
            find_all=True,
        ):
            row = row_match.groupdict()
            values.append({
                "X": row["symbol"],
                "x": float(row["x"]),
                "y": float(row["y"]),
                "z": float(row["z"])
            })

        return {
            "card_option": units,
            "values": values
        }

    def parse(self) -> dict:
        """
        Returns the entire parsed input file as a flat dictionary.
        Aligns directly with the ESSE pw.x.json schema.
        """
        result = {
            "CONTROL": self.get_namelist("control"),
            "SYSTEM": self.get_namelist("system"),
            "ELECTRONS": self.get_namelist("electrons"),
        }

        cell_params = self.get_card_cell_parameters()
        if cell_params:
            result["CELL_PARAMETERS"] = cell_params

        atomic_positions = self.get_card_atomic_positions()
        if atomic_positions:
            result["ATOMIC_POSITIONS"] = atomic_positions

        return {
            "content": result,
            "version": self.version,
        }

    def validate_schema(self) -> None:
        """
        Validates the parsed content against the ESSE pw.x schema.
        Raises an exception if invalid.
        """
        from mat3ra.esse import ESSE # Lazy import to prevent tight coupling
        es = ESSE()
        pwin_schema = es.get_schema_by_id("apse/file/applications/espresso/7.2/pw.x")
        es.validate(self.parse()["content"], pwin_schema)
