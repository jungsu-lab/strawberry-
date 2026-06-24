from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


NAMESPACE = {"sheet": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
JsonCell = str


@dataclass(frozen=True, slots=True)
class XlsxReadError(Exception):
    path: Path
    detail: str

    def __str__(self) -> str:
        return f"failed to read {self.path}: {self.detail}"


def read_xlsx_records(path: Path) -> list[dict[str, JsonCell]]:
    rows = read_xlsx_rows(path)
    if not rows:
        return []
    headers = _dedupe_headers(rows[0])
    records: list[dict[str, JsonCell]] = []
    for row in rows[1:]:
        record: dict[str, JsonCell] = {}
        for index, header in enumerate(headers):
            if header == "":
                continue
            record[header] = row[index] if index < len(row) else ""
        records.append(record)
    return records


def read_xlsx_rows(path: Path) -> list[list[JsonCell]]:
    try:
        with ZipFile(path) as archive:
            shared_strings = _shared_strings(archive)
            worksheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    except (BadZipFile, ElementTree.ParseError, KeyError) as error:
        raise XlsxReadError(path=path, detail=str(error)) from error

    rows: list[list[JsonCell]] = []
    for row in worksheet.findall(".//sheet:sheetData/sheet:row", NAMESPACE):
        values_by_index: dict[int, JsonCell] = {}
        for cell in row.findall("sheet:c", NAMESPACE):
            index = _column_index(cell.attrib.get("r", "A1"))
            values_by_index[index] = _cell_value(cell, shared_strings)
        if values_by_index:
            width = max(values_by_index) + 1
            rows.append([values_by_index.get(index, "") for index in range(width)])
    return rows


def _shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    except ElementTree.ParseError as error:
        raise XlsxReadError(path=Path("xl/sharedStrings.xml"), detail=str(error)) from error

    values: list[str] = []
    for item in root.findall("sheet:si", NAMESPACE):
        values.append("".join(text.text or "" for text in item.findall(".//sheet:t", NAMESPACE)))
    return values


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> JsonCell:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//sheet:t", NAMESPACE))

    value = cell.find("sheet:v", NAMESPACE)
    if value is None or value.text is None:
        return ""
    raw_value = value.text
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw_value)]
    return raw_value


def _column_index(reference: str) -> int:
    column = "".join(character for character in reference if character.isalpha())
    index = 0
    for character in column.upper():
        index = index * 26 + ord(character) - 64
    return index - 1


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    deduped: list[str] = []
    for header in headers:
        normalized = header.strip()
        if normalized == "":
            deduped.append("")
            continue
        count = seen.get(normalized, 0)
        seen[normalized] = count + 1
        deduped.append(normalized if count == 0 else f"{normalized}.{count + 1}")
    return deduped
