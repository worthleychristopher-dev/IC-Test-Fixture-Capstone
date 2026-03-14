from reportlab.platypus import SimpleDocTemplate, KeepTogether, Paragraph, Table, Spacer, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from ICTestFixture.core.testvector import TestVector  # for printing class attributes into PDF report

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
    headerRow = [[Paragraph(col) for col in cols]]
    dataStr = [[str(k), str(v)] for k, v in data.items()]
    dataRows =  [[Paragraph(cell) for cell in row] for row in dataStr]
    table = Table(headerRow + dataRows, COL_WIDTHS)
    table.setStyle(TABLE_STYLE)

    story.append(Paragraph(title, style=STYLES["Heading2"]))
    story.append(table)
    story.append(LINE)
    return

def exportToPdf(chipInfo: dict, testVecs: list[TestVector], filename: str):
    # TODO: make formatting better
    # TODO: add overall pass/fail at top of doc
    report = SimpleDocTemplate(filename)

    story = []
    story.append(LINE)

    if chipInfo: dictToTable(story, "Chip Info", chipInfo, ["Parameter", "Description"])
    if TestVector.pinMap: dictToTable(story, "Pin Map", TestVector.pinMap, ["Pin Name", "Pin"])
    dictToTable(story, "Global Parameters", TestVector.globalParams, ["Parameter", "Value"])
    story.append(Paragraph("Tests", style=STYLES["Heading2"]))

    for testVec in testVecs:
        status = "PASS" if testVec.passed else "FAIL"
        color = "green" if testVec.passed else "red"
        story.append(Paragraph(f"{testVec.testName}: <font color={color}>{status}</font>", style=STYLES["Heading3"]))
        story.append(SPACER)
        
        vecTable, metadata = testVec.exportAsTable()
        
        # use metadata of vecTable to format the table
        inputSpan = metadata["inputSpan"]
        outputSpan = metadata["outputSpan"]
        includeVcc = metadata["includeVcc"]
        numRows = metadata["numRows"]
        numVcc = metadata["numVcc"]

        outCol = lambda colNum: 2 * colNum + int(includeVcc) + inputSpan
        startRow = lambda rowNum : rowNum * numVcc + 2 # +2 because starts on 3rd row, 
        endRow = lambda rowNum : rowNum * numVcc + 2 + numVcc - 1 # numVcc-1 spans row vertically, counting from rowNum

        # default table styling for tests
        styleCmd = [
            ("ALIGN", (0,0), (-1,-1), "CENTER"), # centers all text in every cell
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), # aligns to middle vertically
            ("GRID", (0,0), (-1,-1), 0.5, colors.black), # create grid for all cells of 0.5 thickness
            ("SPAN", (0,0), (inputSpan-1,0)), # span Inputs header
            (("SPAN", (inputSpan+int(includeVcc),0), (-1,0))) # span outputs/results header
        ]
        if includeVcc:
            styleCmd.append(("SPAN", (inputSpan,0), (inputSpan,1))) # combine VCC cell with empty cell below
            for i in range(numRows):
                # input rows
                for inCol in range(inputSpan):
                    styleCmd.append(("SPAN", (inCol, startRow(i)), (inCol, endRow(i))))
                # output rows
                for colNum in range(outputSpan):
                    styleCmd.append(("SPAN", (outCol(colNum), startRow(i)), (outCol(colNum), endRow(i))))

        for colNum in range(outputSpan):
            # combines each output and result column for each output pin(s)
            styleCmd.append(("SPAN", (outCol(colNum),1), (outCol(colNum)+1,1)))

        vecTable = Table(vecTable)
        vecTable.setStyle(TableStyle(styleCmd))
        story.append(KeepTogether([vecTable, SPACER])) # avoids error when spacer cannot fit on page

    report.build(story)
    return
