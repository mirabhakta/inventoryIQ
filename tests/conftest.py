import pytest

from services.dataset_cache import reset_caches


@pytest.fixture(autouse=True)
def clear_dataset_caches():
    """Keep cached datasets from leaking between tests."""
    reset_caches()
    yield
    reset_caches()
