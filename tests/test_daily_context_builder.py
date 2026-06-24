from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape
from zipfile import ZipFile

from libsbapi.daily_context_builder import build_daily_context_records
from libsbapi.daily_context_io import write_daily_context_files, write_recommendation_log
from libsbapi.farmwork import CropGrowthStage


class DailyContextBuilderTest(unittest.TestCase):
    def test_builds_daily_contexts_from_core_excel_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            farm_dir = root / "electric"
            farm_dir.mkdir(parents=True)
            _write_xlsx(
                farm_dir / "env_hourly.xlsx",
                [
                    ["수집일", "내부-내부CO2", "내부-내부습도", "내부-내부온도", "외부-외부일사량", "외부-강우감지"],
                    ["2024-10-02 000000", "600", "90", "24", "0", "1"],
                    ["2024-10-02 010000", "620", "80", "26", "500", "0"],
                ],
            )
            _write_xlsx(
                farm_dir / "control_hourly.xlsx",
                [
                    ["수집일", "제어-좌측일중천창 개도율", "제어-좌측일중측창 개도율"],
                    ["2024-10-02 00:00:00", "40", "80"],
                    ["2024-10-02 01:00:00", "60", "100"],
                ],
            )
            _write_xlsx(
                farm_dir / "growth.xlsx",
                [
                    ["조사일", "주차", "엽수(개)", "엽장(mm)", "엽폭(mm)", "화방착과수1(개)", "화방착과수2(개)", "화방착과수3(개)"],
                    ["2024-10-01", "11", "8", "100", "80", "4", "3", "5"],
                ],
            )

            records = build_daily_context_records(root)

            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.farm_id, "electric")
            self.assertEqual(record.context.growth_stage, CropGrowthStage.HARVEST)
            self.assertEqual(record.context.snapshot.inside_temperature_c, 25.0)
            self.assertEqual(record.context.snapshot.inside_humidity_pct, 85.0)
            self.assertEqual(record.context.snapshot.co2_ppm, 610.0)
            self.assertEqual(record.context.snapshot.vent_open_pct, 70.0)
            self.assertEqual(record.context.snapshot.image.fruit_count, 12)
            self.assertEqual(record.context.history.days_since_scouting, 1)

    def test_writes_context_files_and_recommendation_log(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            farm_dir = root / "electric"
            farm_dir.mkdir(parents=True)
            _write_xlsx(
                farm_dir / "env_hourly.xlsx",
                [["수집일", "내부-내부습도", "내부-내부온도"], ["2024-10-02 000000", "90", "26"]],
            )
            _write_xlsx(
                farm_dir / "control_hourly.xlsx",
                [["수집일", "제어-좌측일중천창 개도율"], ["2024-10-02 00:00:00", "10"]],
            )
            _write_xlsx(
                farm_dir / "growth.xlsx",
                [["조사일", "주차", "엽수(개)", "화방착과수1(개)"], ["2024-10-02", "11", "8", "12"]],
            )
            records = build_daily_context_records(root)

            context_paths = write_daily_context_files(records, root / "contexts")
            write_recommendation_log(records, root / "logs" / "daily.jsonl")

            self.assertEqual(len(context_paths), 1)
            context_payload = json.loads(context_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(context_payload["growth_stage"], "harvest")
            log_lines = (root / "logs" / "daily.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(log_lines), 1)
            log_payload = json.loads(log_lines[0])
            self.assertEqual(log_payload["farm_id"], "electric")
            self.assertTrue(log_payload["tasks"])


def _write_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
            "</sheets></workbook>",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>',
        )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


if __name__ == "__main__":
    unittest.main()
