from affiche.main import DEV_CORS_ORIGIN, cors_origins

def test_production_image_allows_nothing_by_default():
    assert cors_origins(is_packaged=True, configured=None) == []

def test_local_checkout_still_allows_the_vite_dev_server():
    assert cors_origins(is_packaged=False, configured=None) == [DEV_CORS_ORIGIN]

def test_an_empty_env_var_is_not_a_grant():
    assert cors_origins(is_packaged=True, configured="") == []

def test_configured_origins_override_in_production():
    assert cors_origins(is_packaged=True, configured="https://affiche.example.com") == [
        "https://affiche.example.com"
    ]

def test_multiple_origins_are_split_and_trimmed():
    assert cors_origins(
        is_packaged=True, configured="https://a.example.com , https://b.example.com"
    ) == ["https://a.example.com", "https://b.example.com"]

def test_blank_entries_are_dropped():
    assert cors_origins(is_packaged=True, configured="https://a.example.com,,  ,") == [
        "https://a.example.com"
    ]

def test_configured_origins_also_override_in_a_local_checkout():
    assert cors_origins(is_packaged=False, configured="https://remote.example.com") == [
        "https://remote.example.com"
    ]
