"""Load embedding-service modules under their own names without letting the
service's top-level `config` module collide with src/admin's `config`
(both are bare top-level modules; whichever lands in sys.modules first
would otherwise be silently reused by the other service's imports)."""
import importlib.util
import sys
from pathlib import Path

EMB = Path(__file__).resolve().parents[2] / 'src' / 'embedding'
TRANSCRIPT = Path(__file__).resolve().parents[2] / 'src' / 'transcript-service'

_EMB_NAMES = ('config', 'surreal_client', 'mcp_transcript', 'embedder',
              'search', 'emb_app')


def _exec(modname, path):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def _isolated(names, loader):
    saved = {k: sys.modules.get(k) for k in names}
    try:
        return loader()
    finally:
        for k, v in saved.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)


def load_embedder():
    """Returns (config, embedder) embedding-service modules.

    Modules keep references to THEIR OWN Config object — tests monkeypatch
    attributes on the returned modules (e.g. emb.Config.EMBEDDING_DOC_PREFIX),
    never os.environ-then-reimport.
    """
    def _load():
        cfg = _exec('config', EMB / 'config.py')
        _exec('surreal_client', EMB / 'surreal_client.py')
        emb = _exec('embedder', EMB / 'embedder.py')
        return cfg, emb

    return _isolated(_EMB_NAMES, _load)


def load_search():
    """Returns (config, embedder, search) modules, isolated."""
    def _load():
        cfg = _exec('config', EMB / 'config.py')
        _exec('surreal_client', EMB / 'surreal_client.py')
        emb = _exec('embedder', EMB / 'embedder.py')
        srch = _exec('search', EMB / 'search.py')
        return cfg, emb, srch

    return _isolated(_EMB_NAMES, _load)


def load_app():
    """Returns (config, embedder, search, app) modules, isolated."""
    def _load():
        cfg = _exec('config', EMB / 'config.py')
        _exec('surreal_client', EMB / 'surreal_client.py')
        _exec('mcp_transcript', EMB / 'mcp_transcript.py')
        emb = _exec('embedder', EMB / 'embedder.py')
        srch = _exec('search', EMB / 'search.py')
        appm = _exec('emb_app', EMB / 'app.py')
        return cfg, emb, srch, appm

    return _isolated(_EMB_NAMES, _load)


def load_transcript_service():
    """Returns (config, fetcher) transcript-service modules, isolated the
    same way (it also has a bare top-level `config`)."""
    def _load():
        cfg = _exec('config', TRANSCRIPT / 'config.py')
        fetcher = _exec('ts_fetcher', TRANSCRIPT / 'fetcher.py')
        return cfg, fetcher

    return _isolated(('config', 'ts_fetcher'), _load)
