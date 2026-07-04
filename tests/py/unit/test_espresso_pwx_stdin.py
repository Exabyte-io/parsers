from mat3ra.esse import ESSE
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.applications.espresso.pw_x.stdin.parser import EspressoPwxStdinParser


def test_espresso_pwx_stdin():
    file_content = get_content_by_reference_path("applications/espresso/v5.4.0/stdin")
    parser = EspressoPwxStdinParser(content=file_content)
    parsed_content = parser.parse()["content"]

    assert parsed_content["CONTROL"]["calculation"] == "scf" # string
    assert parsed_content["CONTROL"]["wf_collect"] is True   # boolean
    assert parsed_content["SYSTEM"]["ecutwfc"] == 40         # integer
    assert parsed_content["SYSTEM"]["degauss"] == 0.005      # float

    # Validate against ESSE schema
    es = ESSE()
    pwin_schema = es.get_schema_by_id("apse/file/applications/espresso/7.2/pw.x")

    # If the parsed_content does not match the schema, es.validate() will raise an exception
    # and fail the test, printing out the exact validation error.
    es.validate(parsed_content, pwin_schema)


def test_get_namelist_parses_indexed_fortran_keys():
    content = """
&SYSTEM
    ibrav = 1
    celldm(1) = 15.9018255
    starting_magnetization(2) = 0.5
/
"""
    parser = EspressoPwxStdinParser(content=content)
    system = parser.get_namelist("SYSTEM")

    assert system["ibrav"] == 1
    assert system["celldm1"] == 15.9018255
    assert system["starting_magnetization2"] == 0.5
