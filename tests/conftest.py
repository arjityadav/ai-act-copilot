"""Loaded by pytest before any test module, so every test gets the same environment, whatever
order the tests run in. (Setting these only in tests/helpers.py made a test's result depend on
whether an earlier test file had imported helpers: test_phase8 run alone hit the real Postgres.)
Integration tests build their Postgres/Redis clients explicitly, so they are unaffected."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("STORE", "memory")
os.environ.setdefault("JOB_MODE", "inline")
