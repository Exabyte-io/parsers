import math
from collections import Counter
from functools import reduce
from typing import Tuple

from mat3ra.esse.models.properties_directory.structural.lattice import LatticeSchema
from mat3ra.made.cell import Cell
from mat3ra.made.lattice import Lattice
from mat3ra.made.cell.primitive_cell import get_primitive_cell_from_config
from mat3ra.utils.constants import COEFFICIENTS

from .parser import EspressoPwxStdinParser

# Maps QE ibrav codes → made/esse Bravais type strings
# fmt: off
IBRAV_TO_LATTICE_TYPE = {
    1:  "CUB",
    2:  "FCC",
    3:  "BCC",  -3: "BCC",
    4:  "HEX",
    5:  "RHL",  -5: "RHL",
    6:  "TET",
    7:  "BCT",
    8:  "ORC",
    9:  "ORCC", -9: "ORCC",
    10: "ORCF",
    11: "ORCI",
    12: "MCL",  -12: "MCL",
    13: "MCLC",
    14: "TRI",
}
# fmt: on


class EspressoPwxStdinMaterial(EspressoPwxStdinParser):
    """
    Translates Espresso PWX stdin syntax intermediate configs into MADE material domain configs.
    """

    def _get_cell_from_ibrav(self, system: dict) -> Tuple[str, float, float, float, float, float, float, Cell]:
        """
        Parses system parameters and uses `made` to calculate the 3x3 primitive matrix.
        """
        ibrav = int(system.get("ibrav", 0))
        lattice_type = IBRAV_TO_LATTICE_TYPE.get(ibrav)
        if lattice_type is None:
            raise ValueError(f"Unsupported ibrav={ibrav}")

        has_celldm = "celldm1" in system

        if has_celldm:
            a = float(system["celldm1"]) * COEFFICIENTS["BOHR_TO_ANGSTROM"]
            b = a * float(system.get("celldm2", 1))
            c = a * float(system.get("celldm3", 1))
            alpha = math.degrees(math.acos(float(system.get("celldm4", 0))))
            beta = math.degrees(math.acos(float(system.get("celldm5", 0))))
            gamma = math.degrees(math.acos(float(system.get("celldm6", 0))))
        else:
            a = float(system.get("a", 1))
            b = float(system.get("b", a))
            c = float(system.get("c", a))
            alpha = (
                math.degrees(math.acos(float(system["cosbc"])))
                if "cosbc" in system
                else float(system.get("alpha", 90))
            )
            beta = (
                math.degrees(math.acos(float(system["cosac"]))) if "cosac" in system else float(system.get("beta", 90))
            )
            gamma = (
                math.degrees(math.acos(float(system["cosab"])))
                if "cosab" in system
                else float(system.get("gamma", 90))
            )

        lattice_config = LatticeSchema(type=lattice_type, a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)
        cell = get_primitive_cell_from_config(lattice_config)

        return lattice_type, a, b, c, alpha, beta, gamma, cell

    @property
    def lattice(self) -> dict:
        system = self.get_namelist("system")
        ibrav = int(system.get("ibrav", 0))

        if ibrav == 0:
            cell_card = self.get_card_cell_parameters()
            if not cell_card:
                raise ValueError("ibrav is 0 but CELL_PARAMETERS card is missing.")

            matrix = [cell_card["values"]["v1"], cell_card["values"]["v2"], cell_card["values"]["v3"]]
            units = cell_card.get("card_option", "alat").lower()

            if units == "alat" and self.celldm1_angstrom:
                matrix = [[val * self.celldm1_angstrom for val in row] for row in matrix]

            # For ibrav=0, explicitly calculate parameters FROM the given vectors
            domain_lattice = Lattice.from_vectors_array(matrix)
            lattice_type = domain_lattice.type.value if hasattr(domain_lattice.type, 'value') else domain_lattice.type
            a, b, c = domain_lattice.a, domain_lattice.b, domain_lattice.c
            alpha, beta, gamma = domain_lattice.alpha, domain_lattice.beta, domain_lattice.gamma
            vectors = domain_lattice.vector_arrays_rounded

        else:
            # For ibrav>0, use made's primitive cell generator to build FCC/BCC vectors
            lattice_type, a, b, c, alpha, beta, gamma, cell = self._get_cell_from_ibrav(system)
            vectors = cell.vector_arrays_rounded

        return {
            "type": lattice_type,
            "a": self.round_array_or_number(float(a), self.PRECISION_MAP["coordinates_cartesian"]),
            "b": self.round_array_or_number(float(b), self.PRECISION_MAP["coordinates_cartesian"]),
            "c": self.round_array_or_number(float(c), self.PRECISION_MAP["coordinates_cartesian"]),
            "alpha": self.round_array_or_number(float(alpha), self.PRECISION_MAP["angles"]),
            "beta": self.round_array_or_number(float(beta), self.PRECISION_MAP["angles"]),
            "gamma": self.round_array_or_number(float(gamma), self.PRECISION_MAP["angles"]),
            "units": {"length": "angstrom", "angle": "degree"},
            "vectors": {
                "a": vectors[0],
                "b": vectors[1],
                "c": vectors[2],
                "alat": 1.0,
            },
        }

    @property
    def basis(self) -> dict:
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return {}

        elements = []
        coordinates = []
        card_option = atomic_positions.get("card_option", "crystal").lower()

        for i, site in enumerate(atomic_positions["values"]):
            elements.append({"id": i, "value": site["X"]})
            coords = [site["x"], site["y"], site["z"]]

            # Apply alat scale if coordinates are given in alat
            if card_option == "alat" and self.celldm1_angstrom:
                coords = [c * self.celldm1_angstrom for c in coords]
                units = "cartesian"
            elif card_option == "angstrom":
                units = "cartesian"
            else:
                units = "crystal"

            # Determine precision based on coordinate units
            precision = self.PRECISION_MAP["coordinates_crystal"] if units == "crystal" else self.PRECISION_MAP["coordinates_cartesian"]
            coordinates.append({"id": i, "value": self.round_array_or_number(coords, precision)})

        return {"units": units, "elements": elements, "coordinates": coordinates}

    @property
    def formula(self) -> str:
        """
        Creates a raw standard formula (e.g. Si4O8)
        """
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return ""

        species = [site["X"] for site in atomic_positions["values"]]
        counts = Counter(species)
        return "".join([f"{el}{cnt}" if cnt > 1 else el for el, cnt in counts.items()])

    @property
    def name(self) -> str:
        """
        Creates a reduced formula acting as the material name (e.g. SiO2)
        """
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return ""

        species = [site["X"] for site in atomic_positions["values"]]
        counts = Counter(species)

        if not counts:
            return ""

        # Greatest Common Divisor to reduce the formula
        divisor = reduce(math.gcd, counts.values())
        return "".join([f"{el}{count//divisor}" if count // divisor > 1 else el for el, count in counts.items()])
