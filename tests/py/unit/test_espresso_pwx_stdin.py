from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.applications.espresso.pw_x.stdin.parser import EspressoPwxStdinParser


def test_espresso_pwx_stdin():
    file_content = get_content_by_reference_path("applications/espresso/v5.4.0/stdin")
    parser = EspressoPwxStdinParser(content=file_content)
    namelist_control = parser.namelist_control
    calculation_value = namelist_control["calculation"]
    assert calculation_value == "scf"
