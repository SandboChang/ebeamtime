from __future__ import annotations

from ebeamtime.native_cache import (
    ENV_NATIVE_CACHE_DIR,
    LEGACY_ENV_NATIVE_CACHE_DIR,
    content_addressed_library_path,
    ensure_cached_native_library,
    native_cache_dir,
)
import ebeamtime.native_cache as native_cache


def test_new_cache_environment_takes_precedence(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy"
    current = tmp_path / "current"
    monkeypatch.setenv(LEGACY_ENV_NATIVE_CACHE_DIR, str(legacy))
    monkeypatch.setenv(ENV_NATIVE_CACHE_DIR, str(current))
    assert native_cache_dir().is_relative_to(current)


def test_legacy_cache_environment_remains_supported(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_NATIVE_CACHE_DIR, raising=False)
    monkeypatch.setenv(LEGACY_ENV_NATIVE_CACHE_DIR, str(tmp_path))
    assert native_cache_dir().is_relative_to(tmp_path)


def test_content_address_changes_with_source_or_build_contract(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_NATIVE_CACHE_DIR, str(tmp_path / "cache"))
    source = tmp_path / "kernel.cu"
    source.write_text("first", encoding="utf-8")
    first = content_addressed_library_path("library.so", sources=(source,), build_key=("one",))
    source.write_text("second", encoding="utf-8")
    second = content_addressed_library_path("library.so", sources=(source,), build_key=("one",))
    third = content_addressed_library_path("library.so", sources=(source,), build_key=("two",))
    assert len({first.name, second.name, third.name}) == 3


def test_compiler_and_native_device_are_part_of_cache_identity(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_NATIVE_CACHE_DIR, str(tmp_path / "cache"))
    source = tmp_path / "kernel.cu"
    source.write_text("source", encoding="utf-8")
    monkeypatch.setattr(native_cache, "native_build_fingerprint", lambda key: (*key, "nvcc=13.3", "device=sm_120"))
    first = content_addressed_library_path("library.so", sources=(source,), build_key=("nvcc", "-arch=native"))
    monkeypatch.setattr(native_cache, "native_build_fingerprint", lambda key: (*key, "nvcc=13.3", "device=sm_100"))
    second = content_addressed_library_path("library.so", sources=(source,), build_key=("nvcc", "-arch=native"))
    assert first != second


def test_cached_library_is_built_once_and_published_atomically(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_NATIVE_CACHE_DIR, str(tmp_path / "cache"))
    source = tmp_path / "kernel.mm"
    source.write_text("source", encoding="utf-8")
    calls = []

    def builder(path):
        calls.append(path)
        path.write_bytes(b"native-library")

    first = ensure_cached_native_library("library.dylib", sources=(source,), build_key=("compiler",), builder=builder)
    second = ensure_cached_native_library("library.dylib", sources=(source,), build_key=("compiler",), builder=builder)
    assert first == second
    assert first.read_bytes() == b"native-library"
    assert len(calls) == 1
    assert not tuple(first.parent.glob(".*.lock"))
    if native_cache.os.name != "nt":
        assert first.parent.stat().st_mode & 0o077 == 0
