import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


models = load("codex_models")
update = load("codex_proxy_update")


def test_pick_latest_in_family():
    ids = ["gpt-5.6-sol", "gpt-6-sol", "gpt-6.1-sol", "gpt-6-sol-mini", "gpt-6-luna", "gpt-image-2"]
    assert models.pick_latest(ids, "sol", "gpt-6-sol") == "gpt-6.1-sol"
    assert models.pick_latest(ids, "luna", "x") == "gpt-6-luna"
    assert models.pick_latest(["gpt-6.10-sol", "gpt-6.9-sol"], "sol", "x") == "gpt-6.10-sol"
    assert models.pick_latest([], "sol", "gpt-6-sol") == "gpt-6-sol"
    assert models.pick_latest(["gpt-6-astra"], "sol", "gpt-6-sol") == "gpt-6-sol"


def test_model_ids_from_response_tolerates_bad_input():
    assert models.model_ids_from_response('{"data":[{"id":"gpt-6-sol"},{"x":1},"s"]}') == ["gpt-6-sol", ""]
    assert models.model_ids_from_response("not json") == []
    assert models.model_ids_from_response('{"data": null}') == []


SCRIPT = 'X=1\nCPA_VERSION="7.3.20"\nCPA_SHA256="' + "a" * 64 + '"\n'


def test_rewrite_script_and_versions():
    out = update.rewrite_script(SCRIPT, "8.0.7", "b" * 64)
    assert 'CPA_VERSION="8.0.7"' in out and 'CPA_SHA256="' + "b" * 64 + '"' in out
    assert update.current_version(out) == "8.0.7"
    assert update.parse_version("v8.0.10") > update.parse_version("8.0.9")
    with pytest.raises(ValueError):
        update.rewrite_script(SCRIPT, "8.0.7", "not-a-sha")
    with pytest.raises(ValueError):
        update.rewrite_script(SCRIPT + SCRIPT, "8.0.7", "b" * 64)
    with pytest.raises(ValueError):
        update.parse_version("8.0.7; rm -rf /")


def test_sha_from_checksums():
    text = f"{'c' * 64}  CLIProxyAPI_8.0.7_linux_amd64.tar.gz\n{'d' * 64}  CLIProxyAPI_8.0.7_linux_amd64_no-plugin.tar.gz\n"
    assert update.sha_from_checksums(text, "CLIProxyAPI_8.0.7_linux_amd64_no-plugin.tar.gz") == "d" * 64
    with pytest.raises(ValueError):
        update.sha_from_checksums(text, "missing.tar.gz")


def test_latest_release_rejects_prerelease():
    fetch = lambda url, accept=None: json.dumps({"tag_name": "v9.0.0", "prerelease": True}).encode()
    with pytest.raises(ValueError):
        update.latest_release(fetch)
    fetch = lambda url, accept=None: json.dumps({"tag_name": "v9.0.0"}).encode()
    assert update.latest_release(fetch) == "9.0.0"


def test_apply_rejects_hash_mismatch(tmp_path, monkeypatch):
    script = tmp_path / "codex_proxy.sh"
    script.write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(update, "SCRIPT", script)
    asset = update.ASSET.format(version="9.0.0")

    def fetch(url, accept=None):
        if url.endswith("checksums.txt"):
            return f"{'e' * 64}  {asset}\n".encode()
        return b"tampered"

    class Args:
        version = "9.0.0"

    with pytest.raises(ValueError):
        update.cmd_apply(Args(), fetch=fetch)
    assert script.read_text(encoding="utf-8") == SCRIPT

    import hashlib
    good = b"binary"
    sha = hashlib.sha256(good).hexdigest()
    fetch2 = lambda url, accept=None: f"{sha}  {asset}\n".encode() if url.endswith("checksums.txt") else good
    update.cmd_apply(Args(), fetch=fetch2)
    assert 'CPA_VERSION="9.0.0"' in script.read_text(encoding="utf-8")
