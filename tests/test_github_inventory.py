import json
import unittest
from unittest.mock import patch

from jarvis.github_inventory import GitHubInventoryError, list_repositories


def repository(name="lippytm/example", private=False):
    return {"full_name": name, "private": private, "default_branch": "main",
            "updated_at": "2026-10-20T17:00:00Z", "html_url": f"https://github.com/{name}"}


class Response:
    def __init__(self, payload, link=""):
        self.payload, self.headers = payload, {"Link": link}

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class GitHubInventoryTests(unittest.TestCase):
    def test_explicit_owner_is_public_even_with_token(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "synthetic-token"}, clear=True), \
                patch("jarvis.github_inventory.urlopen", return_value=Response([repository()])) as network:
            result = list_repositories("lippytm")
        request = network.call_args.args[0]
        self.assertIn("/users/lippytm/repos?", request.full_url)
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual("lippytm/example", result[0]["full_name"])

    def test_environment_owner_also_selects_public_scope(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "synthetic-token", "GITHUB_OWNER": "lippytm"}, clear=True), \
                patch("jarvis.github_inventory.urlopen", return_value=Response([])) as network:
            self.assertEqual([], list_repositories())
        self.assertIn("/users/lippytm/repos?", network.call_args.args[0].full_url)

    def test_ownerless_authenticated_inventory_keeps_existing_scope(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "synthetic-token"}, clear=True), \
                patch("jarvis.github_inventory.urlopen", return_value=Response([repository("other/project", True)])) as network:
            result = list_repositories()
        self.assertIn("/user/repos?", network.call_args.args[0].full_url)
        self.assertEqual("Bearer synthetic-token", network.call_args.args[0].get_header("Authorization"))
        self.assertIs(result[0]["private"], True)

    def test_public_inventory_rejects_private_and_other_owner(self):
        for record in (repository(private=True), repository("other/project")):
            with self.subTest(record=record), patch.dict("os.environ", {}, clear=True), \
                    patch("jarvis.github_inventory.urlopen", return_value=Response([record])):
                with self.assertRaises(GitHubInventoryError):
                    list_repositories("lippytm")

    def test_unexpected_shapes_are_rejected(self):
        for payload in ({"message": "unexpected"}, [None], [{"full_name": "lippytm/x"}],
                        [repository(private="false")], [repository() | {"updated_at": 7}]):
            with self.subTest(payload=payload), patch.dict("os.environ", {}, clear=True), \
                    patch("jarvis.github_inventory.urlopen", return_value=Response(payload)):
                with self.assertRaises(GitHubInventoryError):
                    list_repositories("lippytm")

    def test_reads_all_pages(self):
        first = [repository(f"lippytm/repo-{i}") for i in range(100)]
        with patch.dict("os.environ", {}, clear=True), patch("jarvis.github_inventory.urlopen", side_effect=[
                Response(first, '<https://api.github.com/users/lippytm/repos?page=2>; rel="next"'),
                Response([repository("lippytm/final")])]) as network:
            result = list_repositories("lippytm")
        self.assertEqual(101, len(result))
        self.assertEqual(2, network.call_count)

    def test_pagination_cap_fails_instead_of_truncating(self):
        pages = [Response([repository(f"lippytm/repo-{page}-{i}") for i in range(100)]) for page in range(2)]
        with patch.dict("os.environ", {}, clear=True), patch("jarvis.github_inventory._MAX_PAGES", 2), \
                patch("jarvis.github_inventory.urlopen", side_effect=pages):
            with self.assertRaisesRegex(GitHubInventoryError, "incomplete inventory"):
                list_repositories("lippytm")

    def test_duplicate_page_fails(self):
        page = [repository(f"lippytm/repo-{i}") for i in range(100)]
        with patch.dict("os.environ", {}, clear=True), \
                patch("jarvis.github_inventory.urlopen", side_effect=[Response(page), Response(page)]):
            with self.assertRaisesRegex(GitHubInventoryError, "repeated"):
                list_repositories("lippytm")

    def test_owner_cannot_change_url_path(self):
        with patch("jarvis.github_inventory.urlopen") as network:
            with self.assertRaises(GitHubInventoryError):
                list_repositories("../private/repos")
        network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
