import pytest


def test_sctransform_not_offered():
    from backend.rna import _normalization as n
    assert "sctransform" not in n.KNOWN_METHODS
