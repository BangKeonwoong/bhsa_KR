from ctt_viewer.api import _cache_cfg, _cache_cfg_tree

def test_cache_cfg_no_app_context():
    assert _cache_cfg() == (300, 60)
    assert _cache_cfg_tree(True) == (600, 120)
    assert _cache_cfg_tree(False) == (120, 60)
