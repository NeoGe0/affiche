import pytest

from affiche.app.service_configuration.model.service_configuration import (
    ServiceConfiguration,
    ServiceType,
)
from affiche.app.service_configuration.service.configuration_repository import (
    ConfigurationRepository,
)

def _config(name: str = "tvmaze", **overrides) -> ServiceConfiguration:
    fields = dict(name=name, type=ServiceType.PROVIDER, url="https://api.tvmaze.com",
                  token="", enabled=False)
    fields.update(overrides)
    return ServiceConfiguration(**fields)

def test_saving_the_same_service_twice_updates_it(clean_session):
    repo = ConfigurationRepository(clean_session)

    repo.save(_config(enabled=False))
    saved = repo.save(_config(enabled=True))

    assert saved.enabled is True
    assert repo.get_service_configuration("tvmaze").enabled is True

def test_a_second_save_does_not_create_a_second_row(clean_session):
    repo = ConfigurationRepository(clean_session)

    repo.save(_config())
    repo.save(_config(enabled=True))

    assert len(repo.find_service_configurations(ServiceType.PROVIDER)) == 1

def test_a_rotated_token_replaces_the_stored_one(clean_session):
    repo = ConfigurationRepository(clean_session)

    repo.save(_config("tmdb", token="old-token", enabled=True))
    repo.save(_config("tmdb", token="new-token", enabled=True))

    assert repo.get_service_configuration("tmdb").token == "new-token"

def test_services_are_stored_independently(clean_session):
    repo = ConfigurationRepository(clean_session)

    repo.save(_config("tmdb", token="tmdb-token", enabled=True))
    repo.save(_config("tvmaze", enabled=False))

    assert repo.get_service_configuration("tmdb").enabled is True
    assert repo.get_service_configuration("tvmaze").enabled is False

def test_an_unsaved_service_reads_as_none(clean_session):
    assert ConfigurationRepository(clean_session).get_service_configuration("nope") is None

@pytest.mark.parametrize("enabled", [True, False])
def test_enabled_round_trips_both_ways(clean_session, enabled):
    repo = ConfigurationRepository(clean_session)

    repo.save(_config(enabled=not enabled))
    repo.save(_config(enabled=enabled))

    assert repo.get_service_configuration("tvmaze").enabled is enabled
