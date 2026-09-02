import json

from mat3ra.esse import ESSE
from mat3ra.parsers.applications.lmc.deposition.process import LmcDepositionProcess

# A deposition record as the laboratory system writes it, abridged from a combinatorial
# aluminium-scandium nitride run. Kept inline rather than as a fixture file so the mapping under
# test and its input can be read together.
DEPOSITION_RECORD = {
    "form": "htem:deposition",
    "format": "lmc-1.0",
    "username": "Yeageun",
    "instrument": "pdac_com11",
    "number": 26,
    "date": "3/2/2026",
    "presputter_time": 10,
    "sputter_time": 75,
    "notes": "AlScN combi library\nRotation: 60",
    "gas": {
        "cracker": {"enabled": False},
        "cryoshroud": False,
        "dep_torr": 0.003,
        "base_torr": 1e-7,
        "gasses": [{"gas": "N2", "flow": 7}, {"gas": "Ar", "flow": 13}],
    },
    "targets": [
        {"material": "AlSc", "position": "TL", "supply": "RF", "fwd_pwr": 150, "refl_pwr": 0, "gun_angle": 0.3}
    ],
    "substrate": {
        "substrates": [{"material": "d Si"}, {"material": "Pt Si"}],
        "config": "S4C1",
        "bias": {"enabled": False},
        "rotation": {"enabled": True, "frequency": 60},
    },
    "temp": {"setpoint": 100},
    "heating": {"enabled": True},
    "anneal": {"enabled": False},
}

ANNEAL_STAGE_RECORD = {
    "form": "htem:process_stage",
    "format": "lmc-1.0",
    "username": "Andriy",
    "instrument": "pdac_com5",
    "number": 1558,
    "stage": 2,
    "date": "12/16/2021",
    "stage_type": "annealing",
    "stage_instrument": "rta1",
    "gas": {"cracker": {"enabled": False}, "gasses": [{"gas": "N2", "flow": 100}]},
    "temp": {"setpoint": 600, "ideal": 900},
    "ramp_time": 1,
    "anneal_time": 3,
    "subsample_id": "R12",
}


def test_lmc_deposition_parses_the_record():
    parser = LmcDepositionProcess(content=json.dumps(DEPOSITION_RECORD))
    parsed = parser.parse()

    assert parsed["version"] == "lmc-1.0"
    assert parsed["content"]["number"] == 26
    assert parser.is_process_stage is False


def test_lmc_deposition_translates_to_a_process_config():
    config = LmcDepositionProcess(content=DEPOSITION_RECORD).to_dict()

    assert config["categories"]["subtype"] == "sputtering"
    assert config["identifiers"] == [{"scheme": "lmc", "value": "26"}]

    stage = config["stages"][0]
    target = next(source for source in stage["sources"] if source["kind"] == "target")
    assert target["formula"] == "AlSc"
    assert target["supply"] == "rf"
    assert target["power"]["forward"] == {"value": 150, "units": "W"}

    nitrogen = next(source for source in stage["sources"] if source.get("formula") == "N2")
    assert nitrogen["role"] == "reactive"
    assert nitrogen["flowRate"] == {"value": 7, "units": "sccm"}

    argon = next(source for source in stage["sources"] if source.get("formula") == "Ar")
    assert argon["role"] == "sputtering"

    # Implicit units in the source record are made explicit.
    assert stage["environment"]["pressure"] == {"value": 0.003, "units": "Torr"}

    # Pre-sputter and deposition are separate steps, linked into a flowchart.
    assert [step["type"] for step in stage["steps"]] == ["pre_sputter", "deposition"]
    assert stage["steps"][0]["head"] is True
    assert stage["steps"][0]["next"] == "deposition"
    assert stage["steps"][1]["duration"] == {"value": 75, "units": "min"}
    assert stage["steps"][1]["setpoints"]["substrateRotation"] == {"value": 60, "units": "rpm"}


def test_lmc_process_stage_translates_an_anneal():
    parser = LmcDepositionProcess(content=ANNEAL_STAGE_RECORD)
    config = parser.to_dict()

    assert parser.is_process_stage is True
    stage = config["stages"][0]
    assert stage["index"] == 2
    assert stage["categories"]["type"] == "annealing"
    # The stage ran on a different instrument from the run it belongs to.
    assert stage["instrument"]["shortName"] == "rta1"
    assert [step["type"] for step in stage["steps"]] == ["ramp", "anneal"]
    # temp.ideal is a reading of what the chamber reached, temp.setpoint is what was asked for.
    assert stage["environment"]["temperature"] == {"value": 900, "units": "degC"}
    assert stage["steps"][1]["setpoints"]["temperature"] == {"value": 600, "units": "degC"}


def test_lmc_deposition_config_validates_against_the_esse_process_schema():
    config = LmcDepositionProcess(content=DEPOSITION_RECORD).to_dict()

    esse = ESSE()
    process_schema = esse.get_schema_by_id("process")

    # If the config does not match the schema, validate() raises and fails the test with the
    # exact validation error.
    esse.validate(config, process_schema)
