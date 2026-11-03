"""Unit-тесты проверки паспортных данных и обработки источников данных."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from main import find_passports, is_valid_passport, read_text_file, read_web_page


class TestPassportValidation(unittest.TestCase):
    def test_supported_formats(self) -> None:
        samples = ("1234567890", "1234 567890", "0000 000000", "9999999999")
        for record in samples:
            with self.subTest(record=record):
                self.assertTrue(is_valid_passport(record))

    def test_invalid_records(self) -> None:
        samples = (
            "", "123456789", "12345678901", "1234 56789", "1234 5678901",
            "12345 67890", "1234567 890",
            "12 34 567890",          # запись с пробелами 2+2+6 не поддерживается
            "1234-567890", "1234  567890", "1234\t567890", "1234\xa0567890",
            "12AB 567890", "1234 56789O", "1234 567890a",
            " 1234 567890", "1234 567890 ", "1234 567890\n", "1234567890\n",
            "١٢٣٤ ٥٦٧٨٩٠",           # арабо-индийские цифры
        )
        for record in samples:
            with self.subTest(record=record):
                self.assertFalse(is_valid_passport(record))

    def test_non_string_input_returns_false(self) -> None:
        self.assertFalse(is_valid_passport(None))  # type: ignore[arg-type]
        self.assertFalse(is_valid_passport(1234567890))  # type: ignore[arg-type]


class TestPassportSearch(unittest.TestCase):
    def test_finds_all_supported_formats(self) -> None:
        text = "Иванов: 4512 345678; Петров: 4609123456"
        self.assertEqual(find_passports(text), ["4512 345678", "4609123456"])

    def test_removed_format_is_not_found(self) -> None:
        self.assertEqual(find_passports("Паспорт 45 12 345678"), [])

    def test_duplicates_are_removed_across_formats(self) -> None:
        text = "4512 345678, затем снова 4512345678 и 4512 345678"
        self.assertEqual(find_passports(text), ["4512 345678"])

    def test_order_of_first_appearance_is_kept(self) -> None:
        text = "2222 222222 1111111111 2222222222"
        self.assertEqual(
            find_passports(text), ["2222 222222", "1111111111"]
        )

    def test_no_matches_and_empty_text(self) -> None:
        self.assertEqual(find_passports("Здесь нет паспортных данных"), [])
        self.assertEqual(find_passports(""), [])
        self.assertEqual(find_passports(None), [])  # type: ignore[arg-type]

    def test_punctuation_around_match_is_allowed(self) -> None:
        samples = (
            "(4512 345678)", "Паспорт: 4512 345678.", "4512345678, 4609123456;",
            "серия и номер:4512 345678",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertTrue(find_passports(text))

    def test_does_not_match_inside_longer_text(self) -> None:
        samples = (
            "112345678901",        # 12 цифр подряд
            "1234 5678901",       # номер длиннее шести цифр
            "12345 678901",
            "A4512345678",        # буква слева
            "4512345678B",        # буква справа
            "4512345678-1",       # дефис справа
            "7-4512345678",       # дефис слева
            "ID_4512345678",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(find_passports(text), [])


class TestFileReading(unittest.TestCase):
    def test_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("Клиент: 4512 345678", encoding="utf-8")
            self.assertIn("4512 345678", read_text_file(path))

    def test_missing_file_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Файл не найден"):
            read_text_file("this_file_should_not_exist_12345.txt")

    def test_invalid_utf8_raises_unicode_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_bytes(b"\xff\xfe\xfa")
            with self.assertRaises(UnicodeError):
                read_text_file(path)


class TestWebReading(unittest.TestCase):
    def test_rejects_invalid_urls(self) -> None:
        for url in ("example.com", "ftp://example.com", "https://", ""):
            with self.subTest(url=url), self.assertRaises(ValueError):
                read_web_page(url)

    def test_rejects_non_string_url(self) -> None:
        with self.assertRaises(ValueError):
            read_web_page(None)  # type: ignore[arg-type]

    @patch("main.requests.get")
    def test_reads_page_text_and_sets_timeout(self, mock_get: Mock) -> None:
        response = Mock()
        response.text = "Паспорт 4512 345678"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        self.assertIn("4512 345678", read_web_page("https://example.com"))
        mock_get.assert_called_once_with("https://example.com", timeout=10)

    @patch("main.requests.get", side_effect=requests.Timeout("timeout"))
    def test_network_error_is_wrapped(self, mock_get: Mock) -> None:
        with self.assertRaisesRegex(RuntimeError, "Не удалось загрузить страницу"):
            read_web_page("https://example.com")
        mock_get.assert_called_once()

    @patch("main.requests.get")
    def test_http_error_is_wrapped(self, mock_get: Mock) -> None:
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = response
        with self.assertRaises(RuntimeError):
            read_web_page("https://example.com/missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
