
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl import load_workbook


def delete_all_rows(ws: Worksheet) -> None:
    '''
    Deletes all the rows in a worksheet.
    '''
    ws.delete_rows(1, ws.max_row)


def new_table(ws: Worksheet, table_headers: list[str], table_rows: list[dict], table_name: str) -> None:

    # Be sure to first delete the existing rows if you want the table to start on row 1
    delete_all_rows(ws)

    ws.append(table_headers)

    # add rows of data
    for row in table_rows:
        if isinstance(row, dict):
            ws.append([row[h] for h in table_headers])
        else:
            ws.append(row)

    xlscols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    for i in range(26):
        for j in range(26):
            xlscols.append(xlscols[i] + xlscols[j])

    table = Table(
        displayName=table_name,
        ref=f'A1:{xlscols[len(table_headers)-1]}{len(table_rows) + 1}'
    )

    # Add a default style with striped rows and banded columns
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )

    ws.add_table(table)


def new_wb_with_tables(filename: str, descriptors: list[dict]) -> None:
    '''
    Creates and returns a new workbook containing new worksheets each containing a new table.
    The descriptors param is a list of dicts that should look like this:
    [
        {
            table_headers: list[str],
            table_rows: list[list | dict],
            table_name: str,
            sheet_name: str = 'Sheet1'
        },
        {
            table_headers: list[str],
            table_rows: list[list | dict],
            table_name: str,
            sheet_name: str = 'Sheet1'
        }
    ]
    '''
    wb = Workbook()
    active_sheet_name = wb.active.title
    for d in descriptors:
        new_table(wb.create_sheet(d['sheet_name']), d['table_headers'], d['table_rows'], d['table_name'])
    del wb[active_sheet_name]
    wb.save(filename)
