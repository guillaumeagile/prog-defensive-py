import dataclasses

import pytest
from expression import Error, Ok

from solution_etats_illegaux import Config, ConfirmedOrder, DraftOrder, confirm, ship


def test_commande_vide_ne_peut_pas_etre_confirmee():
    assert confirm(DraftOrder("o-1")) == Error("an order needs at least one line to be confirmed")


def test_commande_avec_lignes_est_confirmee_puis_expediee():
    result = confirm(DraftOrder("o-1", ("book",)))
    assert result == Ok(ConfirmedOrder("o-1", ("book",)))
    match result:
        case Ok(ok=confirmed):
            assert ship(confirmed) == "order o-1 shipped with 1 line(s)"
        case Error():
            raise AssertionError("la confirmation devait réussir")


def test_config_est_immuable():
    config = Config("postgres://db", 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_retries = 99  # type: ignore[misc]
