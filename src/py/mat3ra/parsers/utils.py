from typing import Any

def cast_fortran_string(val: str) -> Any:
    """
    Casts Fortran namelist string values to Python native types.
    Handles Fortran booleans (.true., .t.) and float exponents (1.0d0).
    """
    val_lower = val.lower()

    # Handle booleans
    if val_lower in [".true.", ".t.", "true"]:
        return True
    if val_lower in [".false.", ".f.", "false"]:
        return False

    # Handle integers
    try:
        return int(val)
    except ValueError:
        pass

    # Handle floats (replace Fortran 'd'/'D' exponent with 'e')
    try:
        return float(val_lower.replace("d", "e"))
    except ValueError:
        pass

    # Return as string (assumes surrounding quotes are already stripped by caller)
    return val

# TODO: implement
class FortranNamelistParser(object):
    pass
