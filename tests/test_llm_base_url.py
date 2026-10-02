import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm import LLMClient


class LlmBaseUrlTest(unittest.TestCase):
    def _mock_response(self):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "ok",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }
        return resp

    @patch("llm.requests.post")
    def test_chat_auth_error_fails_without_retrying_other_bases(self, mock_post):
        resp = MagicMock()
        resp.status_code = 401
        resp.json.return_value = {
            "error": {
                "message": "Authentication Fails, Your api key is invalid",
                "type": "authentication_error",
            }
        }
        err = Exception("401 Client Error: Authorization Required")
        err.response = resp
        resp.raise_for_status.side_effect = err
        mock_post.return_value = resp

        client = LLMClient(
            api_key="bad-key",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com,https://fallback.invalid",
        )

        with self.assertRaises(Exception):
            client.chat([{"role": "user", "content": "hello"}])

        self.assertEqual(mock_post.call_count, 1)

    @patch("llm.requests.post")
    def test_chat_appends_v1_when_base_is_root(self, mock_post):
        mock_post.return_value = self._mock_response()
        client = LLMClient(
            api_key="test-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com",
        )

        client.chat([{"role": "user", "content": "hello"}])

        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.openai.com/v1/chat/completions",
        )

    @patch("llm.requests.post")
    def test_chat_keeps_versioned_base(self, mock_post):
        mock_post.return_value = self._mock_response()
        client = LLMClient(
            api_key="test-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
        )

        client.chat([{"role": "user", "content": "hello"}])

        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.openai.com/v1/chat/completions",
        )

    @patch("llm.requests.post")
    def test_chat_uses_full_endpoint_directly(self, mock_post):
        mock_post.return_value = self._mock_response()
        client = LLMClient(
            api_key="test-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1/chat/completions",
        )

        client.chat([{"role": "user", "content": "hello"}])

        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.openai.com/v1/chat/completions",
        )


if __name__ == "__main__":
    unittest.main()


class LlmRequestTimeoutTest(unittest.TestCase):
    def _ok(self):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        return resp

    @patch("llm.requests.post")
    def test_default_timeout_is_120(self, mock_post):
        mock_post.return_value = self._ok()
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("LLM_REQUEST_TIMEOUT", None)
            LLMClient(api_key="k", model="m", base_url="http://127.0.0.1:1/v1").chat([{"role": "user", "content": "hi"}])
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 120)

    @patch("llm.requests.post")
    def test_timeout_from_env(self, mock_post):
        mock_post.return_value = self._ok()
        with patch.dict("os.environ", {"LLM_REQUEST_TIMEOUT": "600"}):
            LLMClient(api_key="k", model="m", base_url="http://127.0.0.1:1/v1").chat([{"role": "user", "content": "hi"}])
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 600)

    def test_bad_values_fall_back(self):
        import llm
        with patch.dict("os.environ", {"LLM_REQUEST_TIMEOUT": "abc"}):
            self.assertEqual(llm.resolve_request_timeout(), 120)
        with patch.dict("os.environ", {"LLM_REQUEST_TIMEOUT": "1"}):
            self.assertEqual(llm.resolve_request_timeout(), 10)
