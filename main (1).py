"""Лабораторная работа № 2: регулярные выражения и unit-тестирование.

Тема: проверка и поиск синтаксически корректных паспортных данных
(вариант 25).

Поддерживаемые форматы записи (серия — 4 цифры, номер — 6 цифр):
    1234567890   — слитно;
    1234 567890  — серия и номер через один пробел.
"""

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

# Только ASCII-цифры: класс \d в Python принимает и цифры других письменностей.
_DIGIT = r"[0-9]"
_PASSPORT_BODY = (
    r"(?:"
    rf"{_DIGIT}{{4}} {_DIGIT}{{6}}"
    rf"|{_DIGIT}{{10}}"
    r")"
)
PASSPORT_FULL_PATTERN = re.compile(_PASSPORT_BODY)
# Не допускаем извлечение части более длинной записи: слева и справа от
# совпадения не должно быть букв, цифр, подчёркивания и дефиса.
# Точка, запятая и скобки допустимы (конец предложения, перечисление).
_WORD = r"0-9A-Za-zА-Яа-яЁё_-"
PASSPORT_SEARCH_PATTERN = re.compile(
    rf"(?<![{_WORD}]){_PASSPORT_BODY}(?![{_WORD}])"
)


def is_valid_passport(value: str) -> bool:
    """Вернуть True, если вся строка — паспортные данные поддерживаемого формата."""
    if not isinstance(value, str) or not value:
        return False
    return PASSPORT_FULL_PATTERN.fullmatch(value) is not None


def find_passports(text: str) -> list[str]:
    """Найти уникальные паспортные данные в тексте в порядке первого появления.

    Записи «1234 567890» и «1234567890» считаются одним и тем же паспортом,
    поэтому при удалении повторов сравниваются только цифры.
    """
    if not isinstance(text, str) or not text:
        return []

    unique: list[str] = []
    seen: set[str] = set()
    for record in PASSPORT_SEARCH_PATTERN.findall(text):
        digits = record.replace(" ", "")
        if digits not in seen:
            seen.add(digits)
            unique.append(record)
    return unique


def read_text_file(file_path: str | Path) -> str:
    """Прочитать UTF-8-файл; поднять понятную ошибку при проблеме с чтением."""
    path = Path(file_path)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Файл не найден: {path}") from error
    except UnicodeError as error:
        raise UnicodeError(f"Файл не является корректным UTF-8: {path}") from error
    except OSError as error:
        raise OSError(f"Не удалось прочитать файл {path}: {error}") from error


def read_web_page(url: str) -> str:
    """Загрузить HTTP(S)-страницу и вернуть её текст.

    Raises:
        ValueError: URL не является полным HTTP(S)-адресом.
        RuntimeError: возникла ошибка запроса или HTTP-статуса.
    """
    if not isinstance(url, str):
        raise ValueError("URL должен быть строкой.")
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Введите полный URL, начинающийся с http:// или https://.")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Не удалось загрузить страницу: {error}") from error
    return response.text


def show_results(text: str) -> None:
    """Вывести уникальные найденные записи или сообщение об отсутствии совпадений."""
    records = find_passports(text)
    if not records:
        print("Паспортные данные не найдены.")
        return

    print(f"Найдено уникальных записей паспортных данных: {len(records)}")
    for number, record in enumerate(records, start=1):
        print(f"{number}. {record}")


def run_interactive() -> None:
    """Запустить консольное меню программы."""
    while True:
        print("\nПроверка и поиск паспортных данных")
        print("1 — проверить одну запись")
        print("2 — найти паспортные данные в файле")
        print("3 — найти паспортные данные на веб-странице")
        print("4 — найти паспортные данные во введённом тексте")
        print("0 — выход")
        choice = input("Выберите действие: ").strip()

        try:
            if choice == "1":
                record = input("Введите серию и номер паспорта: ")
                if is_valid_passport(record):
                    print("Запись соответствует выбранному формату.")
                else:
                    print("Некорректные паспортные данные.")
            elif choice == "2":
                show_results(read_text_file(input("Путь к текстовому файлу: ").strip()))
            elif choice == "3":
                show_results(read_web_page(input("Введите URL страницы: ").strip()))
            elif choice == "4":
                show_results(input("Введите текст для поиска: "))
            elif choice == "0":
                print("Работа завершена.")
                return
            else:
                print("Такого пункта нет. Выберите 0, 1, 2, 3 или 4.")
        except (ValueError, OSError, RuntimeError) as error:
            print(f"Ошибка: {error}")


def main() -> None:
    """Обработать аргументы командной строки и запустить выбранный режим."""
    parser = argparse.ArgumentParser(
        description="Проверка и поиск синтаксически корректных паспортных данных."
    )
    parser.add_argument("--demo", action="store_true", help="поиск в демонстрационном файле")
    parser.add_argument("--file", default="sample.txt", help="путь к текстовому файлу")
    args = parser.parse_args()

    if not args.demo:
        run_interactive()
        return
    try:
        show_results(read_text_file(args.file))
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
