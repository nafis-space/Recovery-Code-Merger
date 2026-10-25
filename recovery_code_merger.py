import glob
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _register_font(font_name, patterns, fallback):
    font_dirs = [
        os.path.expanduser("~/.local/share/fonts"),
        os.path.expanduser("~/.fonts"),
        "/usr/local/share/fonts",
        "/usr/share/fonts",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
        "C:/Windows/Fonts",
    ]
    for pattern in patterns:
        for font_dir in font_dirs:
            matches = sorted(
                glob.glob(os.path.join(font_dir, "**", pattern), recursive=True)
            )
            if matches:
                try:
                    pdfmetrics.registerFont(TTFont(font_name, matches[0]))
                    return font_name
                except (OSError, ValueError):
                    continue
    return fallback


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.HexColor("#6b7280"))
            self.drawRightString(
                letter[0] - 42,
                24,
                f"Page {self._pageNumber} of {page_count}",
            )
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def create_dynamic_recovery_pdf(input_folder, output_pdf_path, num_columns=1):
    if num_columns != 1:
        raise ValueError("The print-friendly layout uses exactly one column.")
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    title_font = _register_font(
        "RecoveryHeadline",
        [
            "*Mozilla*Headline*.ttf",
            "*Oswald*Bold*.ttf",
            "*Montserrat*Bold*.ttf",
            "*LiberationSans-Bold.ttf",
        ],
        "Helvetica-Bold",
    )
    details_font = _register_font(
        "RecoveryCondensed",
        [
            "*Roboto*Condensed*.ttf",
            "*LiberationSansNarrow*.ttf",
            "*LiberationSans-Regular.ttf",
        ],
        "Helvetica",
    )
    codes_font = _register_font(
        "RecoveryMono",
        [
            "*JetBrainsMono*Regular*.ttf",
            "*SourceCodePro*Regular*.ttf",
            "*LiberationMono-Regular.ttf",
        ],
        "Courier",
    )

    page_width, page_height = letter
    margin = 42
    doc = BaseDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=78,
        bottomMargin=48,
        title="Unified Recovery Code Ledger",
        author="Recovery Code PDF Maker",
    )
    frame = Frame(
        margin,
        48,
        page_width - 2 * margin,
        page_height - 126,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="main",
    )

    def draw_header(pdf_canvas, _doc):
        pdf_canvas.saveState()
        pdf_canvas.setFont(title_font, 22)
        pdf_canvas.setFillColor(colors.HexColor("#172554"))
        pdf_canvas.drawCentredString(
            page_width / 2, page_height - 42, "Unified Recovery Code Ledger"
        )
        pdf_canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        pdf_canvas.setLineWidth(0.8)
        pdf_canvas.line(margin, page_height - 54, page_width - margin, page_height - 54)
        pdf_canvas.restoreState()

    doc.addPageTemplates(
        [PageTemplate(id="RecoveryLedger", frames=[frame], onPage=draw_header)]
    )

    styles = getSampleStyleSheet()
    app_style = ParagraphStyle(
        "AppName",
        parent=styles["Normal"],
        fontName=details_font,
        fontSize=13,
        leading=16,
        textColor=colors.white,
    )
    meta_style = ParagraphStyle(
        "AccountId",
        parent=styles["Normal"],
        fontName=details_font,
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#dbeafe"),
    )
    code_style = ParagraphStyle(
        "RecoveryCode",
        parent=styles["Normal"],
        fontName=codes_font,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111827"),
        splitLongWords=1,
        wordWrap="CJK",
    )
    empty_style = ParagraphStyle(
        "EmptyFolder",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    files_found = sorted(
        (
            filename
            for filename in os.listdir(input_folder)
            if filename.lower().endswith(".txt")
            and os.path.isfile(os.path.join(input_folder, filename))
        ),
        key=lambda filename: (filename.casefold(), filename),
    )
    story = []
    records_found = 0
    if not files_found:
        story.append(Paragraph("No .txt recovery files were found.", empty_style))
    else:
        for filename in files_found:
            file_path = os.path.join(input_folder, filename)
            with open(file_path, "r", encoding="utf-8-sig") as file:
                lines = [line.strip() for line in file if line.strip()]

            if not lines:
                continue

            records_found += 1
            app_name = lines[0]
            account_id = lines[1] if len(lines) > 1 else ""
            recovery_codes = lines[2:] if len(lines) > 2 else []

            header = Table(
                [
                    [Paragraph(escape(app_name), app_style)],
                    [
                        Paragraph(
                            escape(
                                f"ID/Email: {account_id}"
                                if account_id
                                else "ID/Email: not specified"
                            ),
                            meta_style,
                        )
                    ],
                ],
                colWidths=[doc.width],
            )
            header.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e3a5f")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (0, 0), 7),
                        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                        ("TOPPADDING", (0, 1), (0, 1), 0),
                        ("BOTTOMPADDING", (0, 1), (0, 1), 7),
                    ]
                )
            )
            story.append(header)

            if recovery_codes:
                code_columns = min(4, len(recovery_codes))
                code_rows = []
                for index in range(0, len(recovery_codes), code_columns):
                    row = [
                        Paragraph(escape(code), code_style)
                        for code in recovery_codes[index:index + code_columns]
                    ]
                    if code_columns == 2 and len(row) == 1:
                        row.append("")
                    code_rows.append(row)

                code_table = Table(
                    code_rows,
                    colWidths=[doc.width / code_columns] * code_columns,
                    hAlign="LEFT",
                    splitByRow=1,
                )
                code_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(code_table)
            else:
                story.append(
                    Paragraph("No recovery codes listed.", empty_style)
                )
            story.append(Spacer(1, 12))

        if records_found == 0:
            story.append(Paragraph("No recovery data was found in the .txt files.", empty_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {output_pdf_path}")


if __name__ == "__main__":
    INPUT_FOLDER = "./recovery_txt_files"
    OUTPUT_PDF = "Dynamic_Unified_Recovery.pdf"
    create_dynamic_recovery_pdf(INPUT_FOLDER, OUTPUT_PDF)
