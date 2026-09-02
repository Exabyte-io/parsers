import json
from typing import Any, Dict

from mat3ra.parsers import BaseParser


class LmcDepositionParser(BaseParser):
    """
    Parser for the laboratory management system deposition records written by combinatorial
    sputtering chambers, in the `lmc-1.0` format.

    Unlike the application parsers in this package, no regular expressions are involved: the
    source records are already JSON. What this parser contributes is knowing which of its keys
    are set points, which are readings, and what the implicit units are, none of which the file
    states. Those units are asserted here rather than guessed downstream:

        base_torr, dep_torr    Torr
        flow                   sccm
        fwd_pwr, refl_pwr      W
        volts                  V
        setpoint, ideal        degC
        presputter_time        min
        sputter_time           min
        ramp_time              min
        anneal_time            min
        frequency (rotation)   rpm

    Two record types share the format. A `htem:deposition` is a single run; a
    `htem:process_stage` is one stage of a multi-stage run and adds `stage`, `stage_type` and
    `stage_instrument`, so that a deposition followed by an anneal in a different chamber is two
    records with the same run number.
    """

    DEPOSITION_FORM = "htem:deposition"
    PROCESS_STAGE_FORM = "htem:process_stage"

    UNITS = {
        "pressure": "Torr",
        "flow_rate": "sccm",
        "power": "W",
        "voltage": "V",
        "temperature": "degC",
        "time": "min",
        "rotation_rate": "rpm",
    }

    def __init__(self, content, version: str = "lmc-1.0"):
        """
        Args:
            content (str or dict): file content, as read from the record or already decoded.
            version (str): the record's `format` value.
        """
        super().__init__(content, version=version)

    @property
    def record(self) -> Dict[str, Any]:
        """
        The record as a dictionary, accepting either a JSON string or an already-decoded object.
        """
        if isinstance(self.content, dict):
            return self.content
        return json.loads(self.content)

    @property
    def form(self) -> str:
        """
        Which of the two record types this is: `htem:deposition` or `htem:process_stage`.
        """
        return self.record.get("form", self.DEPOSITION_FORM)

    @property
    def is_process_stage(self) -> bool:
        return self.form == self.PROCESS_STAGE_FORM

    @property
    def run_number(self) -> Any:
        """
        The run number, which is what ties the stages of one multi-stage run together.
        """
        return self.record.get("number")

    def parse(self) -> Dict[str, Any]:
        """
        Returns the record in the intermediate format, i.e. as it is written, with the version
        attached. Translation into a domain config is the job of LmcDepositionProcess.
        """
        return {
            "content": self.record,
            "version": self.record.get("format", self.version),
        }
