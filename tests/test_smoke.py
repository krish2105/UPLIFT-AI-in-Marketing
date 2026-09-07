"""The green bar. If this fails, nothing else in the suite means anything.

`import services.api` alone proves nothing — implicit namespace packages make
any directory importable. So this asserts the package actually declares itself.
"""

import services.api


def test_package_declares_itself():
    assert services.api.APP == "MAWSIM"
    assert services.api.COURSE == "AI 208"


def test_brand_is_declared_fictional_in_code():
    """The fictional-brand disclaimer is not only a README line."""
    assert services.api.BRAND == "SIDRA"
    assert services.api.BRAND_IS_FICTIONAL is True
