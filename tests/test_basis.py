import pytest

from bstocks_alpha.features.basis import reference_basis, reference_basis_bps


def test_reference_basis() -> None:
    assert reference_basis(101.0, 100.0) == pytest.approx(0.01)
    assert reference_basis_bps(101.0, 100.0) == pytest.approx(100.0)


def test_reference_basis_rejects_nonpositive_reference() -> None:
    with pytest.raises(ValueError):
        reference_basis(100.0, 0.0)
