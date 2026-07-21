"""Version-correct PyInstaller hook for the SciPy 1.18 runtime pin."""

from PyInstaller.utils.hooks import check_requirement


hiddenimports = ["scipy.special._ufuncs_cxx"]

# scipy.special._cdflib existed from 1.13 through 1.17 and was removed in 1.18.
if check_requirement("scipy >= 1.13.0, < 1.18.0"):
    hiddenimports.append("scipy.special._cdflib")
if check_requirement("scipy >= 1.14.0"):
    hiddenimports.append("scipy.special._special_ufuncs")
