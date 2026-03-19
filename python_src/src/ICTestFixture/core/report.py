from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# default style for document
STYLES = getSampleStyleSheet()
SPACER = Spacer(1, 12)
LINE = HRFlowable(width="100%", thickness=1, lineCap="square", color="black", spaceBefore=10, spaceAfter=10)
# defines style for 2 column table
# coordinate pairs are (col, row) with (0,0) as top left cell, (-1,-1) as bottom right cell
COL_WIDTHS = [1.25 * inch, 1 * inch]
TABLE_STYLE = TableStyle([
    ("VALIGN", (0,0), (-1,-1), "TOP"), # align to top vertically
    ("ALIGN", (0,0), (-1,-1), "LEFT"), # aligh to left horizontally
    ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black), # line below header columns
    ("LINEBEFORE", (1,0), (1,-1), 0.5, colors.black) # line after first column
])

def dictToTable(story: list, title: str, data: dict, cols: list[str]):
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

def exportToPdf(chip_info: dict, test_vecs: list[TestVector], filename: str):
    # TODO: make formatting better
    # TODO: add overall pass/fail at top of doc
    report = SimpleDocTemplate(filename)

    story = []
    story.append(LINE)
    global_params = test_vecs[0].global_params
    pin_map = test_vecs[0].pin_map

    if chip_info: dictToTable(story, "Chip Info", chip_info, ["Parameter", "Description"])
    if pin_map: dictToTable(story, "Pin Map", pin_map, ["Pin Name", "Pin"])
    dictToTable(story, "Global Parameters", global_params, ["Parameter", "Value"])
    story.append(Paragraph("Tests", style=STYLES["Heading2"]))

    for test_vec in test_vecs:
        status = "PASS" if test_vec.passed else "FAIL"
        color = "green" if test_vec.passed else "red"
        story.append(Paragraph(f"{test_vec.test_name}: <font color={color}>{status}</font>", style=STYLES["Heading3"]))
        story.append(SPACER)
        
        vec_table, metadata = test_vec.export_as_table()
        
        # use metadata of vec_table to format the table
        input_span = metadata["input_span"]
        output_span = metadata["output_span"]
        include_vcc = metadata["include_vcc"]
        num_rows = metadata["num_rows"]
        num_vcc = metadata["num_vcc"]

        out_col = lambda col_num: 2 * col_num + int(include_vcc) + input_span
        start_row = lambda row_num : row_num * num_vcc + 2 # +2 because starts on 3rd row, 
        end_row = lambda row_num : row_num * num_vcc + 2 + num_vcc - 1 # num_vcc-1 spans row vertically, counting from row_num

        # default table styling for tests
        style_cmd = [
            ("ALIGN", (0,0), (-1,-1), "CENTER"), # centers all text in every cell
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), # aligns to middle vertically
            ("GRID", (0,0), (-1,-1), 0.5, colors.black), # create grid for all cells of 0.5 thickness
            ("SPAN", (0,0), (input_span-1,0)), # span Inputs header
            (("SPAN", (input_span+int(include_vcc),0), (-1,0))) # span outputs/results header
        ]
        if include_vcc:
            style_cmd.append(("SPAN", (input_span,0), (input_span,1))) # combine VCC cell with empty cell below
            for i in range(num_rows):
                # input rows
                for in_col in range(input_span):
                    style_cmd.append(("SPAN", (in_col, start_row(i)), (in_col, end_row(i))))
                # output rows
                for col_num in range(output_span):
                    style_cmd.append(("SPAN", (out_col(col_num), start_row(i)), (out_col(col_num), end_row(i))))

        for col_num in range(output_span):
            # combines each output and result column for each output pin(s)
            style_cmd.append(("SPAN", (out_col(col_num),1), (out_col(col_num)+1,1)))

        vec_table = Table(vec_table, repeatRows=2)
        vec_table.setStyle(TableStyle(style_cmd))
        story.append(vec_table)
        story.append(SPACER)

    report.build(story)
    return
