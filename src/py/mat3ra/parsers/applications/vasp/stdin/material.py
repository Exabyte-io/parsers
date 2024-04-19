from pymatgen.analysis.structure_analyzer import SpacegroupAnalyzer

from .parser import VASPStdinParser

_ = VASPStdinParser.round_array_or_number


class VASPStdinMaterialParser(VASPStdinParser):
    def lattice_vectors(self):
        """
        Returns lattice vectors.

        Reference:
            func: express.parsers.mixins.ionic.IonicDataMixin.lattice_vectors
        """
        precision = self.PRECISION_MAP["coordinates_cartesian"]
        return {
            "vectors": {
                "a": _(self.structure.lattice.matrix.tolist()[0], precision),
                "b": _(self.structure.lattice.matrix.tolist()[1], precision),
                "c": _(self.structure.lattice.matrix.tolist()[2], precision),
                "alat": 1.0,
            }
        }

    def lattice_bravais(self):
        """
        Returns lattice bravais.

        Reference:
            func: express.parsers.mixins.ionic.IonicDataMixin.lattice_bravais
        """
        precision_coordinates = self.PRECISION_MAP["coordinates_cartesian"]
        precision_angles = self.PRECISION_MAP["angles"]
        return {
            "type": self._lattice_type(),
            "a": _(self.structure.lattice.a, precision_coordinates),
            "b": _(self.structure.lattice.b, precision_coordinates),
            "c": _(self.structure.lattice.c, precision_coordinates),
            "alpha": _(self.structure.lattice.alpha, precision_angles),
            "beta": _(self.structure.lattice.beta, precision_angles),
            "gamma": _(self.structure.lattice.gamma, precision_angles),
            "units": {"length": "angstrom", "angle": "degree"},
        }

    def _lattice_type(self):
        """
        Returns lattice type according to AFLOW (http://aflowlib.org/) classification.

        Returns:
             str
        """
        lattice_only_structure = self.structure.copy().remove_sites(range(1, len(self.structure.sites)))
        structure_ = lattice_only_structure if self.cell_type != "primitive" else self.structure
        try:
            # try getting the lattice type from the lattice only structure
            return self._lattice_type_from_structure(structure_)
        except Exception:
            try:
                # try getting the lattice type from the current structure
                return self._lattice_type_from_structure(self.structure)
            except Exception:
                return "TRI"

    # TODO: use pymatgen or ASE instead
    def _lattice_type_from_structure(self, structure_):
        """
        Returns lattice type according to AFLOW (http://aflowlib.org/) classification.

        Returns:
             str
        """
        analyzer = SpacegroupAnalyzer(structure_, symprec=0.001)
        lattice_type = analyzer.get_lattice_type()
        spg_symbol = analyzer.get_space_group_symbol()

        # TODO: find a better implementation
        if lattice_type == "cubic":
            if "P" in spg_symbol:
                return "CUB"
            elif "F" in spg_symbol:
                return "FCC"
            elif "I" in spg_symbol:
                return "BCC"
        elif lattice_type == "tetragonal":
            if "P" in spg_symbol:
                return "TET"
            elif "I" in spg_symbol:
                return "BCT"
        elif lattice_type == "orthorhombic":
            if "P" in spg_symbol:
                return "ORC"
            elif "F" in spg_symbol:
                return "ORCF"
            elif "I" in spg_symbol:
                return "ORCI"
            elif "C" in spg_symbol:
                return "ORCC"
        elif lattice_type == "hexagonal":
            return "HEX"
        elif lattice_type == "rhombohedral":
            return "RHL"
        elif lattice_type == "monoclinic":
            if "P" in spg_symbol:
                return "MCL"
            elif "C" in spg_symbol:
                return "MCLC"

        return "TRI"

    def basis(self):
        """
        Returns basis.

        Reference:
            func: express.parsers.mixins.ionic.IonicDataMixin.basis
        """
        return {
            "units": "crystal",
            "elements": [{"id": i, "value": v.species_string} for i, v in enumerate(self.structure.sites)],
            "coordinates": [
                {"id": i, "value": _(v.frac_coords.tolist(), self.PRECISION_MAP["coordinates_crystal"])}
                for i, v in enumerate(self.structure.sites)
            ],
        }
