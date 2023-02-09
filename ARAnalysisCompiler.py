
import csv
from datetime import datetime
from SpreadsheetTools import new_wb_with_tables


class ARAnalysisCompiler:

    headers = {
        'Source Facility',
        'Account Number',
        'Financial Class Beginning',
        'Financial Class Ending',
        'ATB Date - Max',
        'ATB Date - Min',
        'Beginning AR Balance',
        'Charges',
        'Admin',
        'Bad Debt',
        'Charity',
        'Contractuals',
        'Denials',
        'Payments',
        'Ending AR Balance',
        'MRA - Estimated Reserve Beginning',
        'MRA - Estimated Reserve Ending'
    }

    def __init__(self):
        self.start_date = None
        self.end_date = None
        self.facility = None
        self.pt_accts = dict()
        pass

    def date(self, string: str) -> datetime:
        return datetime.strptime(string.strip(), '%m/%d/%Y')

    def currency(self, string: str) -> float:
        return round(float(string.strip().replace("-", "0.0").replace("(", "-").replace(",", "").replace(")", "").replace("$", "")), 2)

    def load_file(self, input_file: str) -> list[dict]:
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if not ARAnalysisCompiler.headers.issubset(set(reader.fieldnames)):
                raise ValueError('Input file does not have the correct column headers.')
            for row in reader:
                if not self.facility:
                    self.facility = row['Source Facility'].strip()
                if not self.start_date:
                    self.start_date = self.date(row['ATB Date - Min'])
                if not self.end_date:
                    self.end_date = self.date(row['ATB Date - Max'])
                number = int(row['Account Number'].strip())
                if self.pt_accts.get(number, None):
                    raise ValueError(f'Patient account number {number} appears more than once in the input file.')
                self.pt_accts[number] = {
                    'Number': number,
                    'FC Beginning': row['Financial Class Beginning'],
                    'FC Ending': row['Financial Class Ending'],
                    'Begin Bal': self.currency(row['Beginning AR Balance']),
                    'Charges': self.currency(row['Charges']),
                    'Admin Adj': self.currency(row['Admin']),
                    'Bad Debt WO': self.currency(row['Bad Debt']),
                    'Charity Adj': self.currency(row['Charity']),
                    'Contractual Adj': self.currency(row['Contractuals']),
                    'Denial WO': self.currency(row['Denials']),
                    'Receipts/Refunds': self.currency(row['Payments']),
                    'Ending Bal': self.currency(row['Ending AR Balance']),
                    'Rsv: Begin Bal': -self.currency(row['MRA - Estimated Reserve Beginning']),
                    'Rsv: Ending Bal': -self.currency(row['MRA - Estimated Reserve Ending'])
                }
        pass

    def add_reserve_activity(self) -> None:

        fields = ['Charges', 'Admin Adj', 'Bad Debt WO', 'Charity Adj', 'Contractual Adj', 'Denial WO']

        for pt in self.pt_accts.values():

            # initialize the cumulative balances
            cum_acct_bal = pt['Begin Bal']
            cum_rsv_bal = pt['Rsv: Begin Bal']

            # calculate the reserve activity and add it to the patient account
            for field in fields:
                rsv_field = 'Rsv: ' + field
                pt[rsv_field] = 0.0 if cum_acct_bal == 0.0 else round(pt[field] / cum_acct_bal * cum_rsv_bal, 2)
                cum_acct_bal += pt[field]
                cum_rsv_bal += pt[rsv_field]

            # calculate the change in the reserve due the the month-end valuation
            pt['Rsv: Releases'] = 0.0
            pt['Rsv: Valuation'] = round(pt['Rsv: Ending Bal'] - cum_rsv_bal, 0)

            # verify that the reserve rolls-forward correctly
            if cum_rsv_bal + pt['Rsv: Valuation'] != pt['Rsv: Ending Bal']:
                raise ValueError(f'Reserve activity does not roll-forward for patient {pt["Number"]}')

            # relcassify the valuation amount if it is attributable to cash receipts
            if pt['Rsv: Begin Bal'] < 0.0 and pt['Rsv: Ending Bal'] == 0.0 and pt['Receipts/Refunds'] < 0.0 and pt['Rsv: Valuation'] > 0.0:
                pt['Rsv: Releases'] = pt['Rsv: Valuation']
                pt['Rsv: Valuation'] = 0.0
        pass

    def add_descriptions(self) -> tuple:

        # group the accounts into three categories
        for pt in self.pt_accts.values():

            bd = pt['Bad Debt WO']
            beg_rsv = pt['Rsv: Begin Bal']
            beg_net = pt['Begin Bal'] + beg_rsv
            pay = pt['Receipts/Refunds']
            chg = pt['Charges']
            end_net = pt['Ending Bal'] + pt['Rsv: Ending Bal']

            desc = ''

            if beg_net > 0.0:
                desc += 'Positive beginning NRV '
            elif beg_net < 0.0:
                desc += 'Negative beginning NRV '
            else:
                desc += 'Zero beginning NRV '

            if chg > 0.0:
                desc += 'having charges, '
            elif chg < 0.0:
                desc += 'having charge reversals, '
            else:
                desc += 'having charges, '

            if bd > 0.0:
                desc += 'bad debt reversal, '

            if pay < 0.0:
                desc += 'cash receipts'
                if abs(pay) > (beg_net + chg + pt['Rsv: Charges']):
                    desc += ' in excess of beginning NRV + net charges'
                desc += ', '
            elif pay > 0.0:
                desc += 'refunds, '
            else:
                desc += 'no cash activity, '

            if end_net > 0.0:
                desc += 'and ending in a debit NRV.'
            elif end_net < 0.0:
                desc += 'and ending in a credit NRV.'
            else:
                desc += 'and ending in a zero NRV.'

            pt['Description'] = desc

        pass

    def write_to_file(self, output_file: str) -> None:
        headers = [h for h in self.pt_accts[next(iter(self.pt_accts))].keys()]
        new_wb_with_tables(
            output_file,
            [
                {
                    'table_headers': headers,  # [h for h in self.pt_accts[0].keys()],
                    'table_rows': self.pt_accts.values(),
                    'table_name': 'PT_ACCT_ROLL',
                    'sheet_name': 'Pt Acct Roll-forward'
                }
            ]
        )
        pass

    def compile(self, facility_name: str, input_file: str, output_file: str) -> None:
        self.load_file(input_file)
        self.add_reserve_activity()
        self.add_descriptions()
        self.write_to_file(output_file)
        pass
