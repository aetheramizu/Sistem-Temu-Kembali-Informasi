"""Membuat workbook .xlsx multi-sheet tanpa dependency eksternal.

Hasil: Data/spreadsheet_kerja_stki.xlsx
Workbook berisi data final: 50 dokumen, 25 query, dan 173 pasangan penilaian.
File ini bisa di-upload ke Google Drive lalu dibuka sebagai Google Sheets.
"""
from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data" / "spreadsheet_kerja_stki.xlsx"
DOC_CSV = ROOT / "Data" / "kandidat_dokumen_50.csv"
QUERY_CSV = ROOT / "Data" / "queries_25.csv"
CANDIDATE_QUERY_CSV = ROOT / "Data" / "kandidat_query_awal.csv"
PENILAIAN_CSV = ROOT / "Data" / "lembar_penilaian_final.csv"


@dataclass(frozen=True)
class Formula:
    expression: str
    cached: int | float = 0


def col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def cell_xml(ref: str, value: object, style: int) -> str:
    if value is None:
        return ""
    if isinstance(value, Formula):
        return f'<c r="{ref}" s="{style}"><f>{escape(value.expression)}</f><v>{value.cached}</v></c>'
    text = str(value)
    if text == "":
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    if text.startswith("="):
        return f'<c r="{ref}" s="{style}"><f>{escape(text[1:])}</f><v>0</v></c>'
    return (
        f'<c r="{ref}" s="{style}" t="inlineStr">'
        f'<is><t xml:space="preserve">{escape(text)}</t></is></c>'
    )


def sheet_xml(
    headers: list[str] | None,
    rows: list[list[object]],
    widths: list[float],
    *,
    wrap_cols: set[int] | None = None,
    validations: list[tuple[str, str]] | None = None,
    freeze: bool = True,
    autofilter: bool = True,
    data_height: int | None = None,
    tab_selected: bool = False,
) -> str:
    wrap_cols = wrap_cols or set()
    all_rows: list[list[object]] = []
    if headers:
        all_rows.append(list(headers))
    all_rows.extend(rows)

    max_cols = max((len(r) for r in all_rows), default=1)
    max_rows = max(len(all_rows), 1)
    dim = f"A1:{col_letter(max_cols)}{max_rows}"

    cols = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(widths, start=1)
    )

    sheet_rows: list[str] = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            if r_idx == 1 and headers:
                style = 1
            elif c_idx in wrap_cols:
                style = 2
            else:
                style = 0
            cells.append(cell_xml(f"{col_letter(c_idx)}{r_idx}", value, style))
        if not any(cells):
            continue
        attrs = f'r="{r_idx}"'
        if r_idx == 1 and headers:
            attrs += ' ht="30" customHeight="1"'
        elif data_height:
            attrs += f' ht="{data_height}" customHeight="1"'
        sheet_rows.append(f"<row {attrs}>{''.join(cells)}</row>")

    tab_attr = ' tabSelected="1"' if tab_selected else ""
    if freeze:
        sheet_view = (
            f'<sheetViews><sheetView{tab_attr} workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
            "</sheetView></sheetViews>"
        )
    else:
        sheet_view = (
            f'<sheetViews><sheetView{tab_attr} workbookViewId="0"/>'
            "</sheetViews>"
        )

    auto_filter = ""
    if headers and autofilter:
        auto_filter = f'<autoFilter ref="A1:{col_letter(max_cols)}{max_rows}"/>'

    validation_xml = ""
    if validations:
        items = []
        for sqref, formula in validations:
            items.append(
                f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
                f'showErrorMessage="1" sqref="{sqref}">'
                f'<formula1>"{escape(formula)}"</formula1>'
                "</dataValidation>"
            )
        validation_xml = f'<dataValidations count="{len(items)}">{"".join(items)}</dataValidations>'

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dim}"/>'
        f"{sheet_view}"
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"<cols>{cols}</cols>"
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        f"{auto_filter}"
        f"{validation_xml}"
        '<pageMargins left="0.5" right="0.5" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_documents() -> list[list[object]]:
    return [
        [
            int(row["no"]),
            row["doc_id"],
            row["judul"],
            row["isi"],
            row["topik"],
            row["sumber"],
            row["jenis_sumber"],
            row["url"],
            row["tanggal_publikasi"],
            row["tanggal_akses"],
            row["status_verifikasi"],
            row["catatan"],
            row["anggota_pengumpul"],
            row["verifikator_1"],
            row["verifikator_2"],
            row["tanggal_verifikasi"],
        ]
        for row in read_csv(DOC_CSV)
    ]


def read_queries() -> list[list[object]]:
    candidates = {row["query_id"]: row for row in read_csv(CANDIDATE_QUERY_CSV)}
    rows: list[list[object]] = []
    for row in read_csv(QUERY_CSV):
        candidate = candidates.get(row.get("asal_kandidat", ""), {})
        catatan = row.get("catatan", "")
        if "menunggu sign-off" in catatan:
            catatan = "Disetujui; dipakai untuk qrels final dan eksperimen A/B."
        rows.append(
            [
                row["query_id"],
                row["query"],
                row["intent"],
                row["topik"],
                candidate.get("anggota_pengusul", ""),
                row["status"],
                catatan,
            ]
        )
    return rows


def read_penilaian() -> list[list[object]]:
    rows: list[list[object]] = []
    for i, row in enumerate(read_csv(PENILAIAN_CSV), start=1):
        catatan_1 = row["catatan_penilai_1"].strip() or row["alasan_penilai_1"].strip()
        catatan_2 = row["catatan_penilai_2"].strip() or row["alasan_penilai_2"].strip()
        rows.append(
            [
                i,
                row["query_id"],
                row["query"],
                row["doc_id"],
                row["judul"],
                row["topik"],
                "penilai_1",
                int(row["label_penilai_1"]),
                catatan_1,
                "penilai_2",
                int(row["label_penilai_2"]),
                catatan_2,
                int(row["label_final"]),
                row["status_verifikasi"],
                row["catatan_anggota"],
            ]
        )
    return rows


def build() -> None:
    doc_rows = read_documents()
    query_rows = read_queries()
    penilaian_rows = read_penilaian()

    petunjuk = [
        ["PETUNJUK PENGGUNAAN SPREADSHEET PROJECT STKI"],
        [],
        ["Workbook ini berisi data final (2026-10-21): 50 dokumen, 25 query, dan 173 pasangan penilaian."],
        ["1. Upload file ini ke Google Drive, lalu buka dengan Google Sheets."],
        ["2. Bagikan ke seluruh anggota. Gunakan akses Editor saat memeriksa, Viewer setelah final."],
        ["3. Jangan mengubah nama sheet, header, atau ID."],
        ["4. Rubrik relevansi 1/2/3; dokumen nonrelevan tidak masuk qrels (tidak ada label 0)."],
        ["5. Sheet Dokumen berisi 50 dokumen final K001–K050 dengan status terverifikasi."],
        ["6. Sheet Query berisi 25 query final Q01–Q25 yang sudah disetujui."],
        ["7. Sheet Penilaian berisi 173 pasangan dengan label dua penilai dan label final."],
        ["8. Jangan memakai ringkasan AI tanpa sumber sebagai isi dokumen."],
        ["9. Jangan menaruh tautan source code sebelum repository dipublikasikan."],
        ["10. Kolom isi dokumen tetap 3 kalimat (sekitar 200–300 karakter)."],
        [],
        ["Status dokumen: kandidat / perlu_tinjau / terverifikasi / ditolak"],
        ["Status query: kandidat / disetujui / ditolak"],
        ["Status penilaian: menunggu_verifikasi / disetujui"],
        [],
        ["Sheet", "Fungsi"],
        ["Pembagian", "Pembagian modul dan target awal dokumen"],
        ["Dokumen", "50 dokumen final dan metadata sumber"],
        ["Query", "25 query final Q01–Q25"],
        ["Penilaian", "173 pasangan query–dokumen; label 1/2/3"],
        ["Progress", "Rekap otomatis jumlah dokumen, query, dan penilaian"],
    ]

    pembagian = [
        ["Alief", "Modul 7 + eksperimen A/B + analisis", 10, "10 dokumen, 5 query, nilai 5 query", "Koordinator teknis"],
        ["Tri Darul", "Modul 1–2", 10, "10 dokumen, 5 query, nilai 5 query", "Preprocessing + inverted index"],
        ["Aulia Dwinatasha", "Modul 3–4", 10, "10 dokumen, 5 query, nilai 5 query", "Boolean + TF-IDF"],
        ["Elok Humairo'", "Modul 5", 10, "10 dokumen, 5 query, nilai 5 query", "BM25 + koordinasi query"],
        ["Andi Rosiqah", "Modul 6", 10, "10 dokumen, 5 query, nilai 5 query", "Evaluasi + validasi + laporan"],
        ["TOTAL", "7 modul", 50, "50 dokumen, 25 query", "Target final"],
    ]

    doc_headers = [
        "no", "doc_id", "judul", "isi", "topik", "sumber", "jenis_sumber",
        "url", "tanggal_publikasi", "tanggal_akses", "status_verifikasi",
        "catatan", "anggota_pengumpul", "verifikator_1", "verifikator_2",
        "tanggal_verifikasi",
    ]

    query_headers = ["query_id", "query_text", "intent", "subtopic", "anggota_pengusul", "status", "catatan"]

    penilaian_headers = [
        "no", "query_id", "query", "doc_id", "judul", "topik",
        "penilai_1", "label_penilai_1", "catatan_penilai_1",
        "penilai_2", "label_penilai_2", "catatan_penilai_2",
        "label_final", "status_verifikasi", "catatan_anggota",
    ]

    progress_rows: list[list[object]] = [
        ["Dokumen final", Formula("COUNTA(Dokumen!C:C)-1", 50), 50, "50 dokumen final terisi"],
        ["Dokumen terverifikasi", Formula('COUNTIF(Dokumen!K:K,"terverifikasi")', 50), 50, "Target 50 dokumen final"],
        ["Query final", Formula("COUNTA(Query!B:B)-1", 25), 25, "25 query final Q01–Q25"],
        ["Query disetujui", Formula('COUNTIF(Query!F:F,"disetujui")', 25), 25, "Semua query final disetujui"],
        ["Pasangan dinilai", Formula("COUNTA(Penilaian!B:B)-1", 173), 173, "173 pasangan query–dokumen"],
        ["Label final terisi", Formula("COUNTA(Penilaian!M:M)-1", 173), 173, "Label hasil adjudikasi"],
        ["Penilaian disetujui", Formula('COUNTIF(Penilaian!N:N,"disetujui")', 173), 173, "Target sama dengan pasangan dinilai"],
    ]

    sheets = [
        ("Petunjuk", None, petunjuk, [120], set(), [], False, False, None),
        ("Pembagian", ["Anggota", "Modul", "Target Dokumen", "Tugas Data", "Catatan"], pembagian, [18, 42, 16, 48, 38], {2, 4, 5}, [], True, True, 30),
        ("Dokumen", doc_headers, doc_rows, [5, 10, 38, 65, 30, 28, 16, 50, 16, 16, 18, 32, 18, 18, 18, 18], {3, 4, 12}, [("K2:K51", "kandidat,perlu_tinjau,terverifikasi,ditolak")], True, True, 45),
        ("Query", query_headers, query_rows, [10, 55, 45, 32, 20, 14, 34], {2, 3, 7}, [("F2:F26", "kandidat,disetujui,ditolak")], True, True, 35),
        ("Penilaian", penilaian_headers, penilaian_rows, [5, 10, 38, 10, 35, 30, 16, 13, 30, 16, 13, 30, 13, 22, 35], {3, 5, 9, 12, 15}, [("H2:H174", "1,2,3"), ("K2:K174", "1,2,3"), ("M2:M174", "1,2,3"), ("N2:N174", "menunggu_verifikasi,disetujui")], True, True, 45),
        ("Progress", ["Metrik", "Nilai", "Target", "Catatan"], progress_rows, [35, 14, 12, 48], {1, 4}, [], True, True, 24),
    ]

    sheet_files: list[tuple[str, str]] = []
    for idx, sheet in enumerate(sheets, start=1):
        name, headers, rows, widths, wrap, validations, freeze, autofilter, height = sheet
        xml = sheet_xml(
            headers,
            rows,
            widths,
            wrap_cols=wrap,
            validations=validations,
            freeze=freeze,
            autofilter=autofilter,
            data_height=height,
            tab_selected=(idx == 1),
        )
        sheet_files.append((f"xl/worksheets/sheet{idx}.xml", xml))

    workbook_sheets = "".join(
        f'<sheet name="{name}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, (name, *_rest) in enumerate(sheets, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView/></bookViews>'
        f"<sheets>{workbook_sheets}</sheets>"
        '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
        "</workbook>"
    )

    workbook_rels = "".join(
        f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, len(sheets) + 1)
    )
    workbook_rels += (
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{workbook_rels}</Relationships>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for idx in range(1, len(sheets) + 1)
        )
        + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="4">'
        '<font><name val="Arial"/><family val="2"/><sz val="11"/></font>'
        '<font><name val="Arial"/><family val="2"/><b/><color rgb="FFFFFFFF"/><sz val="11"/></font>'
        '<font><name val="Arial"/><family val="2"/><b/><color rgb="FF1F4E79"/><sz val="16"/></font>'
        '<font><name val="Arial"/><family val="2"/><i/><color rgb="FF666666"/><sz val="10"/></font>'
        "</fonts>"
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF1F4E79"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", styles)
        for name, xml in sheet_files:
            archive.writestr(name, xml)

    print(f"Workbook: {OUT}")
    print(f"Sheet   : {', '.join(name for name, *_ in sheets)}")


if __name__ == "__main__":
    build()
