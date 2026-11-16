import dataclasses

import pytest
from returns.result import Failure, Success

from solution_etats_illegaux import Config, ConfirmedOrder, DraftOrder, confirm, ship


def test_commande_vide_ne_peut_pas_etre_confirmee():
    assert confirm(DraftOrder("o-1")) == Failure("an order needs at least one line to be confirmed")


def test_commande_avec_lignes_est_confirmee_puis_expediee():
    result = confirm(DraftOrder("o-1", ("book",)))
    assert result == Success(ConfirmedOrder("o-1", ("book",)))
    assert ship(result.unwrap()) == "order o-1 shipped with 1 line(s)"


def test_config_est_immuable():
    config = Config("postgres://db", 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_retries = 99  # type: ignore[misc]
