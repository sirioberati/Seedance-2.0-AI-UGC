#!/usr/bin/env python3
"""Generate the API bug report PDF."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "api-bug-report.pdf"

# Colors
RED = HexColor("#DC2626")
GREEN = HexColor("#16A34A")
ORANGE = HexColor("#EA580C")
BLUE = HexColor("#2563EB")
GRAY_BG = HexColor("#F3F4F6")
DARK = HexColor("#1F2937")
LIGHT_RED = HexColor("#FEE2E2")
LIGHT_GREEN = HexColor("#DCFCE7")
LIGHT_ORANGE = HexColor("#FFF7ED")
LIGHT_BLUE = HexColor("#EFF6FF")
BORDER = HexColor("#D1D5DB")

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle("BigTitle", parent=styles["Title"], fontSize=22, textColor=DARK, spaceAfter=4))
styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=11, textColor=HexColor("#6B7280"), spaceAfter=20))
styles.add(ParagraphStyle("SectionHead", parent=styles["Heading1"], fontSize=16, textColor=DARK, spaceBefore=20, spaceAfter=8))
styles.add(ParagraphStyle("SubHead", parent=styles["Heading2"], fontSize=13, textColor=DARK, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=DARK, spaceAfter=6, leading=14))
styles.add(ParagraphStyle("BodyBold", parent=styles["Normal"], fontSize=10, textColor=DARK, spaceAfter=6, leading=14, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Code", parent=styles["Normal"], fontSize=9, textColor=DARK, fontName="Courier", backColor=GRAY_BG, spaceAfter=6, leading=12, leftIndent=10, rightIndent=10))
styles.add(ParagraphStyle("Bullet", parent=styles["Normal"], fontSize=10, textColor=DARK, spaceAfter=4, leading=14, leftIndent=20, bulletIndent=10))
styles.add(ParagraphStyle("CellText", parent=styles["Normal"], fontSize=8.5, textColor=DARK, leading=11))
styles.add(ParagraphStyle("CellBold", parent=styles["Normal"], fontSize=8.5, textColor=DARK, leading=11, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("CellPass", parent=styles["Normal"], fontSize=8.5, textColor=GREEN, leading=11, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("CellFail", parent=styles["Normal"], fontSize=8.5, textColor=RED, leading=11, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("CellWarn", parent=styles["Normal"], fontSize=8.5, textColor=ORANGE, leading=11, fontName="Helvetica-Bold"))

def make_cell(text, style="CellText"):
    return Paragraph(text, styles[style])

def build():
    doc = SimpleDocTemplate(OUTPUT, pagesize=letter,
                            leftMargin=0.6*inch, rightMargin=0.6*inch,
                            topMargin=0.6*inch, bottomMargin=0.6*inch)
    story = []

    # ── HEADER ──
    story.append(Paragraph("Enhancor API Bug Report", styles["BigTitle"]))
    story.append(Paragraph("Seedance 2.0 Full Access  |  /queue endpoint  |  April 14, 2026", styles["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 12))

    # ── SUMMARY ──
    story.append(Paragraph("Summary", styles["SectionHead"]))
    story.append(Paragraph(
        "The <b>/queue</b> endpoint returns <b>HTTP 503</b> when <b>images[]</b> contains "
        "2 or more URLs. This affects every mode except <b>ugc</b> (which uses products[]/influencers[] instead). "
        "With 1 image, all modes return 200. The jobs still queue and complete on the backend despite the 503 "
        "-- but the <b>requestId is lost</b> in the error response.",
        styles["Body"]
    ))

    # ── THE BUG ──
    story.append(Paragraph("The Bug in One Sentence", styles["SectionHead"]))

    bug_data = [[Paragraph(
        "<b>images[]</b> with 2+ URLs  -->  503 on every mode except ugc. "
        "Same images with 1 URL  -->  200. Job queues anyway but requestId is lost.",
        ParagraphStyle("BugText", parent=styles["Normal"], fontSize=11, textColor=RED, leading=15)
    )]]
    bug_table = Table(bug_data, colWidths=[6.8*inch])
    bug_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_RED),
        ("BOX", (0,0), (-1,-1), 1, RED),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(bug_table)
    story.append(Spacer(1, 16))

    # ── TEST DETAILS ──
    story.append(Paragraph("Test Configuration", styles["SubHead"]))
    story.append(Paragraph("All tests used: <b>type: image-to-video, full_access: true, aspect_ratio: 9:16, duration: 5, resolution: 720p, webhook_url included</b>", styles["Body"]))
    story.append(Paragraph("Images: stock water bottle photo + stock male headshot (completely clean, no restricted content)", styles["Body"]))
    story.append(Spacer(1, 8))

    # ── 1 IMAGE vs 2 IMAGES TABLE ──
    story.append(Paragraph("Core Test: 1 Image vs 2 Images", styles["SubHead"]))

    header = [make_cell("<b>Mode</b>", "CellBold"),
              make_cell("<b>1 image + 1 audio</b>", "CellBold"),
              make_cell("<b>2 images + 1 audio</b>", "CellBold")]
    rows = [
        [make_cell("ugc (products[])"), make_cell("200 OK", "CellPass"), make_cell("200 OK", "CellPass")],
        [make_cell("multi_reference"), make_cell("200 OK", "CellPass"), make_cell("503", "CellFail")],
        [make_cell("lipsyncing"), make_cell("200 OK", "CellPass"), make_cell("503", "CellFail")],
        [make_cell("multi_frame"), make_cell("200 OK", "CellPass"), make_cell("503", "CellFail")],
        [make_cell("first_n_last_frames"), make_cell("200 OK", "CellPass"), make_cell("503", "CellFail")],
    ]

    t = Table([header] + rows, colWidths=[2.2*inch, 2.3*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), white),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, GRAY_BG]),
        ("BOX", (0,0), (-1,-1), 1, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # ── FULL TEST MATRIX ──
    story.append(Paragraph("Full Test Matrix", styles["SectionHead"]))

    fheader = [make_cell("<b>#</b>", "CellBold"),
               make_cell("<b>Mode</b>", "CellBold"),
               make_cell("<b>Images Field</b>", "CellBold"),
               make_cell("<b># Imgs</b>", "CellBold"),
               make_cell("<b>Audio</b>", "CellBold"),
               make_cell("<b>Result</b>", "CellBold")]

    frows = [
        ["1", "ugc", "products[]", "1", "none", ("200 OK", "CellPass")],
        ["2", "ugc", "products[]+influencers[]", "1+1", "none", ("200 OK", "CellPass")],
        ["3", "ugc", "products[]", "2", "none", ("200 OK", "CellPass")],
        ["4", "ugc", "products[]", "1", "audios[] x1", ("200 OK", "CellPass")],
        ["5", "ugc", "products[]+influencers[]", "1+1", "audios[] x1", ("200 OK", "CellPass")],
        ["6", "ugc", "products[]", "2", "audios[] x1", ("200 OK", "CellPass")],
        ["7", "ugc", "images[]", "2", "audios[] x1", ("400 err", "CellWarn")],
        ["8", "multi_ref", "images[]", "1", "none", ("200 OK", "CellPass")],
        ["9", "multi_ref", "images[]", "1", "audios[] x1", ("200 OK", "CellPass")],
        ["10", "multi_ref", "images[]", "2", "none", ("503", "CellFail")],
        ["11", "multi_ref", "images[]", "2", "audios[] x1", ("503", "CellFail")],
        ["12", "multi_ref", "image[] (singular)", "2", "none", ("200 *", "CellWarn")],
        ["13", "multi_ref", "image[] (singular)", "2", "audio[] (singular)", ("200 *", "CellWarn")],
        ["14", "multi_ref", "products[]+influencers[]", "1+1", "none", ("200 OK", "CellPass")],
        ["15", "multi_ref", "products[]+influencers[]", "1+1", "audios[] x1", ("500 err", "CellFail")],
        ["16", "lipsyncing", "images[]", "1", "lipsyncing_audio", ("200 OK", "CellPass")],
        ["17", "lipsyncing", "images[]", "2", "lipsyncing_audio", ("503", "CellFail")],
        ["18", "multi_frame", "images[]", "1", "audios[] x1", ("200 OK", "CellPass")],
        ["19", "multi_frame", "images[]", "2", "audios[] x1", ("503", "CellFail")],
        ["20", "first_n_last", "first+last_frame_image", "2", "audios[] x1", ("503", "CellFail")],
    ]

    table_rows = [fheader]
    for row in frows:
        result_text, result_style = row[5]
        table_rows.append([
            make_cell(row[0]),
            make_cell(row[1]),
            make_cell(row[2]),
            make_cell(row[3]),
            make_cell(row[4]),
            make_cell(result_text, result_style),
        ])

    ft = Table(table_rows, colWidths=[0.35*inch, 0.95*inch, 1.7*inch, 0.55*inch, 1.15*inch, 0.75*inch])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), white),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, GRAY_BG]),
        ("BOX", (0,0), (-1,-1), 1, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    story.append(ft)
    story.append(Paragraph("* 200 but backend ignores singular field names -- images not actually used in generation", ParagraphStyle("Footnote", parent=styles["Normal"], fontSize=8, textColor=HexColor("#6B7280"), spaceAfter=6)))
    story.append(Spacer(1, 12))

    # ── SECONDARY ISSUES ──
    story.append(Paragraph("Secondary Issues", styles["SectionHead"]))

    story.append(Paragraph("<b>1. Singular field names bypass validation</b>", styles["Body"]))
    story.append(Paragraph(
        'Using <b>image</b> (singular) instead of <b>images</b> (plural) returns 200 with 2+ URLs. '
        'But the backend ignores the field -- images are silently dropped. Same for audio vs audios. '
        'The gateway accepts unknown fields without error, giving a false success.',
        styles["Body"]
    ))

    story.append(Paragraph("<b>2. False 'restricted material' error</b>", styles["Body"]))
    story.append(Paragraph(
        'When multi_reference uses <b>products[] + influencers[]</b> with <b>audios[]</b>, the API returns '
        'HTTP 500 "This image contains restricted material" -- even on completely clean images (water bottle, '
        'stock headshot). Same images + audio work fine in ugc mode. The content filter misfires when '
        'audios[] is combined with products[]/influencers[] on multi_reference.',
        styles["Body"]
    ))

    story.append(Paragraph("<b>3. 503 jobs still complete on backend</b>", styles["Body"]))
    story.append(Paragraph(
        'Confirmed via webhook.site callbacks: jobs that received 503 responses still queued, generated videos, '
        'and sent COMPLETED webhooks with video URLs. The requestId is just lost in the 503 response. '
        'This means callers who retry on 503 (standard HTTP practice) create <b>duplicate jobs and waste credits</b>.',
        styles["Body"]
    ))
    story.append(Spacer(1, 12))

    # ── EXPECTED BEHAVIOR ──
    story.append(Paragraph("Expected Behavior", styles["SectionHead"]))

    expected_data = [[Paragraph(
        "The /queue endpoint should return <b>HTTP 200</b> with "
        '<b>{"success": true, "requestId": "..."}</b> immediately after accepting the job, '
        "regardless of the number of images. URL validation and content checks should happen "
        "asynchronously in the queue worker -- same as ugc mode already does.",
        ParagraphStyle("ExpText", parent=styles["Normal"], fontSize=10, textColor=BLUE, leading=14)
    )]]
    exp_table = Table(expected_data, colWidths=[6.8*inch])
    exp_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_BLUE),
        ("BOX", (0,0), (-1,-1), 1, BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(exp_table)
    story.append(Spacer(1, 16))

    # ── HYPOTHESIS ──
    story.append(Paragraph("Root Cause Hypothesis", styles["SectionHead"]))
    story.append(Paragraph(
        "The gateway downloads and validates all <b>images[]</b> URLs synchronously before returning a response. "
        "When there are 2+ images, this exceeds the gateway timeout and returns 503 -- even though the job was "
        "already passed to the queue. <b>ugc mode</b> routes products[]/influencers[] through a different code path "
        "that handles them asynchronously, which is why it never returns 503.",
        styles["Body"]
    ))
    story.append(Spacer(1, 20))

    # ── FOOTER ──
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Tested by Claude Code  |  API: apireq.enhancor.ai/api/enhancor-ugc-full-access/v1  |  April 14, 2026",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=HexColor("#9CA3AF"), alignment=TA_CENTER)
    ))

    doc.build(story)
    print(f"PDF saved to {OUTPUT}")

if __name__ == "__main__":
    build()
