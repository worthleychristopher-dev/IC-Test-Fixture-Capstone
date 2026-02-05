from reportlab.platypus import SimpleDocTemplate, KeepTogether, Paragraph, Table, Spacer, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
# for printing class attributes into PDF report
from test_vector import TestVector

# default style for document
STYLES = getSampleStyleSheet()
SPACER = Spacer(1, 12)
LINE = HRFlowable(width="100%", thickness=1, lineCap="square", color="black", spaceBefore=10, spaceAfter=10)
COL_WIDTHS = [1.25 * inch, 1 * inch]
TABLE_STYLE = TableStyle([
    ("VALIGN", (0,0), (-1,-1), "TOP"), # align to top vertically
    ("ALIGN", (0,0), (-1,-1), "LEFT"), # aligh to left horizontally
    ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black), # line below header columns
    ("LINEBEFORE", (1,0), (1,-1), 0.5, colors.black) # line after first column
])

def dict_to_table(story: list, title: str, data: dict, cols: list[str]):
    """
        Converts a dictionary to a table and appends it to the story list.
        Formats as parameters and values into two columns
    """
    # convert strings to paragraph for text-wrapping
    header_row = [[Paragraph(col) for col in cols]]
    data_str = [[str(k), str(v)] for k, v in data.items()]
    data_rows =  [[Paragraph(cell) for cell in row] for row in data_str]
    table = Table(header_row + data_rows, COL_WIDTHS)
    table.setStyle(TABLE_STYLE)

    story.append(Paragraph(title, style=STYLES["Heading2"]))
    story.append(table)
    story.append(LINE)
    return

def export_to_pdf(chip_info: dict, test_vecs: list[TestVector], filename: str):
    # TODO: make formatting better
    report = SimpleDocTemplate(filename)

    story = []
    story.append(LINE)

    if chip_info: dict_to_table(story, "Chip Info", chip_info, ["Parameter", "Description"])
    if TestVector.pin_map: dict_to_table(story, "Global Parameters", TestVector.pin_map, ["Pin Name", "Pin"])
    dict_to_table(story, "Global Parameters", TestVector.global_params, ["Parameter", "Value"])
    story.append(Paragraph("Tests", style=STYLES["Heading2"]))

    # generate test vector tables
    # abstract this to test vector likely
    for test_vec in test_vecs:
        status = "PASS" if test_vec.passed else "FAIL"
        color = "green" if test_vec.passed else "red"
        story.append(Paragraph(f"{test_vec.test_name}: <font color={color}>{status}</font>", style=STYLES["Heading3"]))
        story.append(SPACER)
        
        input_span = len(test_vec.inputs)
        output_span = len(test_vec.outputs)
        # default table styling
        style_cmd = [
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("SPAN", (0,0), (input_span-1,0)), # span inputs header
            ("SPAN", (input_span,0), (-1,0)) # span outputs/results header
        ]
        # combines each output and result column for each output pin(s)
        for col in range(output_span):
            style_cmd.append(("SPAN", ((2*col)+input_span,1), ((2*col)+input_span+1,1)))

        vec_table = Table(test_vec.export_as_table())
        vec_table.setStyle(TableStyle(style_cmd))
        story.append(KeepTogether([vec_table, SPACER])) # avoids error when spacer cannot fit on page

    report.build(story)
    return