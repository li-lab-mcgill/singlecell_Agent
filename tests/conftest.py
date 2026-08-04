"""Pytest bootstrap — import real scientific dependencies before collection.

Several legacy test modules inject fake ``pandas`` / ``numpy`` / ``anndata``
stubs into ``sys.modules`` at import time, each guarded by
``if "<mod>" not in sys.modules``. When such a module is collected before a
test that needs the *real* library, the fake shadows the real one for the rest
of the session (surfacing as ``TypeError: DataFrame() takes no arguments`` deep
inside anndata). Importing the real libraries here — during pytest startup,
before any test module is collected — makes those guards see the modules
already present and skip the fakes whenever the libraries are installed.

In a minimal environment without these libraries the imports fail silently and
the legacy fakes are injected exactly as before, so this is a no-op there.
"""

for _mod in ("numpy", "pandas", "anndata", "requests"):
    try:
        __import__(_mod)
    except Exception:
        pass
