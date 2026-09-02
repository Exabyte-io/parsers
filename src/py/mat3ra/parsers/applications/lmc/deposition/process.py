from typing import Any, Dict, List, Optional

from .parser import LmcDepositionParser

# The lab system names a gas by its formula and a target by the material loaded into the gun.
# ESSE wants a stable identifier per source that a step can point at, so one is derived from
# the formula. Identifiers are lowercased because they are keys, not display names.
GAS_ROLES = {
    "N2": "reactive",
    "O2": "reactive",
    "NH3": "reactive",
    "Ar": "sputtering",
    "He": "carrier",
}

# `stage_type` in the source record is a technique, in the vocabulary ESSE categorizes with.
STAGE_TYPE_TO_CATEGORIES = {
    "deposition": {
        "tier1": "experimental",
        "tier2": "synthesis",
        "tier3": "vapor_deposition",
        "type": "physical_vapor_deposition",
        "subtype": "sputtering",
    },
    "annealing": {
        "tier1": "experimental",
        "tier2": "synthesis",
        "tier3": "post_processing",
        "type": "annealing",
    },
}


class LmcDepositionProcess(LmcDepositionParser):
    """
    Translates a laboratory deposition record into an ESSE `process` config.

    The mapping is mostly mechanical, with three decisions worth stating:

    1. One record becomes one process with one stage. A multi-stage run is several records
       sharing a run number, so assembling them into one process with several stages is the
       caller's job -- this class does not guess which records belong together.
    2. `presputter_time` and `sputter_time` become two steps rather than two fields, because the
       chamber does two distinct things and a step is what ESSE gives a duration to.
    3. `temp.setpoint` and `temp.ideal` are a set point and a reading of the same quantity. The
       set point goes on the step; the reading goes on the stage environment, where it describes
       what the chamber actually did.
    """

    UNITS = LmcDepositionParser.UNITS

    def _quantity(self, value: Optional[float], unit_kind: str) -> Optional[Dict[str, Any]]:
        """Wraps a bare number from the record as an ESSE quantity, or drops it if absent."""
        if value is None:
            return None
        return {"value": value, "units": self.UNITS[unit_kind]}

    @property
    def categories(self) -> Dict[str, Any]:
        stage_type = self.record.get("stage_type", "deposition")
        return STAGE_TYPE_TO_CATEGORIES.get(stage_type, STAGE_TYPE_TO_CATEGORIES["deposition"])

    @property
    def sources(self) -> List[Dict[str, Any]]:
        """
        Targets and gases as ESSE process sources. Forward and reflected power are kept apart
        because their difference is what reaches the target.
        """
        sources: List[Dict[str, Any]] = []

        for target in self.record.get("targets", []):
            material = target.get("material", "")
            source = {
                "kind": "target",
                "id": material.lower() or "target",
                "formula": material,
                "position": target.get("position"),
                "supply": (target.get("supply") or "").lower() or None,
                "power": {
                    "forward": self._quantity(target.get("fwd_pwr"), "power"),
                    "reflected": self._quantity(target.get("refl_pwr"), "power"),
                },
                "voltage": self._quantity(target.get("volts"), "voltage"),
                "gunAngle": target.get("gun_angle"),
            }
            sources.append(self._without_empty_values(source))

        for gas in self.record.get("gas", {}).get("gasses", []):
            formula = gas.get("gas", "")
            source = {
                "kind": "gas",
                "id": formula.lower() or "gas",
                "formula": formula,
                "role": GAS_ROLES.get(formula, "background"),
                "flowRate": self._quantity(gas.get("flow"), "flow_rate"),
            }
            sources.append(self._without_empty_values(source))

        return sources

    @property
    def environment(self) -> Dict[str, Any]:
        """
        Chamber conditions. The working pressure is the one the deposition ran at; the base
        pressure, measured before the run, is carried as metadata because ESSE's environment
        holds one pressure.
        """
        gas = self.record.get("gas", {})
        environment = {
            "pressure": self._quantity(gas.get("dep_torr"), "pressure"),
            "temperature": self._quantity(self.record.get("temp", {}).get("ideal"), "temperature"),
            "atmosphere": "vacuum",
        }
        return self._without_empty_values(environment)

    @property
    def steps(self) -> List[Dict[str, Any]]:
        """
        The operations the record describes, linked into the flowchart ESSE walks a process by.
        A deposition record has a pre-sputter and a deposition; an anneal record has a ramp and
        a hold.
        """
        temperature = self._quantity(self.record.get("temp", {}).get("setpoint"), "temperature")
        rotation = self.record.get("substrate", {}).get("rotation", {})
        setpoints = {
            "temperature": temperature,
            "pressure": self._quantity(self.record.get("gas", {}).get("dep_torr"), "pressure"),
        }
        if rotation.get("enabled") and rotation.get("frequency") is not None:
            setpoints["substrateRotation"] = self._quantity(rotation["frequency"], "rotation_rate")

        candidates = [
            ("pre_sputter", "Pre-sputter", self.record.get("presputter_time"), {}),
            ("deposition", "Deposition", self.record.get("sputter_time"), self._without_empty_values(setpoints)),
            ("ramp", "Ramp", self.record.get("ramp_time"), {}),
            (
                "anneal",
                "Anneal",
                self.record.get("anneal_time"),
                self._without_empty_values({"temperature": temperature}),
            ),
        ]

        steps = []
        for step_type, name, duration, step_setpoints in candidates:
            if duration is None:
                continue
            step = {
                "name": name,
                "flowchartId": step_type,
                "type": step_type,
                "duration": self._quantity(duration, "time"),
            }
            if step_setpoints:
                step["setpoints"] = step_setpoints
            steps.append(step)

        for index, step in enumerate(steps):
            step["head"] = index == 0
            if index + 1 < len(steps):
                step["next"] = steps[index + 1]["flowchartId"]

        return steps

    @property
    def stage(self) -> Dict[str, Any]:
        instrument_name = self.record.get("stage_instrument") or self.record.get("instrument")
        stage = {
            "name": f"{self.record.get('stage_type', 'deposition').capitalize()} on {instrument_name}",
            "index": self.record.get("stage", 1),
            "categories": self.categories,
            # The record names the chamber only by its short name; an instrument entity needs a
            # name, so the short name serves as both until the instrument is looked up by it.
            "instrument": (
                {"name": instrument_name, "shortName": instrument_name} if instrument_name else None
            ),
            "sources": self.sources or None,
            "environment": self.environment or None,
            "steps": self.steps,
            "notes": self.record.get("notes"),
        }
        return self._without_empty_values(stage)

    @staticmethod
    def _without_empty_values(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drops keys the record did not carry. A missing field means the lab system did not record
        it, which is not the same as a zero, so it is left out rather than defaulted.
        """
        return {key: value for key, value in config.items() if value not in (None, {}, [])}

    def _serialize(self) -> Dict[str, Any]:
        """
        Serialize the record as an ESSE process config.

        Returns:
            dict
        """
        substrates = self.record.get("substrate", {}).get("substrates", [])
        process = {
            "name": f"{self.record.get('instrument', 'deposition')} run {self.run_number}",
            "categories": self.categories,
            "properties": ["film_thickness"],
            "status": "finished",
            "identifiers": [{"scheme": "lmc", "value": str(self.run_number)}] if self.run_number else None,
            "operators": [{"name": self.record["username"]}] if self.record.get("username") else None,
            "stages": [self.stage],
            "description": self.record.get("notes"),
            "metadata": {
                "sourceFormat": self.record.get("format"),
                "sourceForm": self.form,
                "basePressure": self._quantity(self.record.get("gas", {}).get("base_torr"), "pressure"),
                "substrates": [substrate.get("material") for substrate in substrates] or None,
                "substrateConfiguration": self.record.get("substrate", {}).get("config"),
                "date": self.record.get("date"),
            },
        }
        process["metadata"] = self._without_empty_values(process["metadata"])
        return self._without_empty_values(process)

    def to_dict(self) -> Dict[str, Any]:
        return self._serialize()
