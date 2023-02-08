
import csv
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
        self.data = dict()

    def currency(self, string: str) -> float:
        return float(string.replace("-", "0.0").replace("(", "-").replace(",", "").replace(")", "").replace("$", ""))

    def load_file(self, input_file: str) -> list[dict]:
        initial_rows = []
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if not ARAnalysisCompiler.headers.issubset(set(reader.fieldnames)):
                raise ValueError('Input file does not have the correct column headers.')
            for row in reader:
                if not self.facility:
                    self.facility = row['Source Facility'].strip()
                if not self.start_date:
                    self.start_date = row['ATB Date - Min'].strip()
                if not self.end_date:
                    self.end_date = row['ATB Date - Max'].strip()
                initial_rows.append({
                    'Number': int(row['Account Number'].strip()),
                    'FC Beginning': row['Financial Class Beginning'].strip(),
                    'FC Ending': row['Financial Class Ending'].strip(),
                    'Begin Bal': self.currency(row['Beginning AR Balance'].strip()),
                    'Charges': self.currency(row['Charges'].strip()),
                    'Admin Adj': self.currency(row['Admin'].strip()),
                    'Bad Debt WO': self.currency(row['Bad Debt'].strip()),
                    'Charity Adj': self.currency(row['Charity'].strip()),
                    'Contractual Adj': self.currency(row['Contractuals'].strip()),
                    'Denial WO': self.currency(row['Denials'].strip()),
                    'Receipts/Refunds': self.currency(row['Payments'].strip()),
                    'Ending Bal': self.currency(row['Ending AR Balance'].strip()),
                    'Rsv: Beginning': -self.currency(row['MRA - Estimated Reserve Beginning'].strip()),
                    'Rsv: Ending': -self.currency(row['MRA - Estimated Reserve Ending'].strip())
                })
        return initial_rows

    def add_reserve_activity(self, pt_accts: list[dict]) -> None:

        # iterate through all the patient accounts
        for pt in pt_accts:

            pt_running_bal = [
                [0.0, pt['Begin Bal']],      # 0
                [pt['Charges'], 0.0],        # 1
                [pt['Admin Adj'], 0.0],      # 2
                [pt['Bad Debt WO'], 0.0],    # 3
                [pt['Charity Adj'], 0.0],    # 4
                [pt['Contractual Adj'], 0.0],  # 5
                [pt['Denial WO'], 0.0],      # 6
                [pt['Receipts/Refunds'], 0.0],  # 7
                [0.0, pt['Ending Bal']],      # 8
            ]

            # update the patient account running balance in the second column of the table above
            for i in range(1, len(pt_running_bal) - 1):
                pt_running_bal[i][1] = pt_running_bal[i - 1][1] + pt_running_bal[i][0]

            # make sure that the ending balance recalculates
            if round(pt_running_bal[7][1], 2) != round(pt_running_bal[8][1], 2):
                for x in pt_running_bal:
                    print(x[0], "\t", x[1])
                raise ValueError(f'Ending balance for patient {pt["number"]} does not recalculate.')

            rsv_running_bal = [
                [0.0, pt['Rsv: Beginning']],  # 0 beginning balance
                [0.0, 0.0],            # 1 charges
                [0.0, 0.0],            # 2 admin
                [0.0, 0.0],            # 3 bd
                [0.0, 0.0],            # 4 charity
                [0.0, 0.0],            # 5 contra
                [0.0, 0.0],            # 6 denials
                [0.0, 0.0],            # 7 releases
                [0.0, 0.0],            # 8 valuation
                [0.0, pt['Rsv: Ending']]  # 9 ending balance
            ]

            # update the running balance of the reserve in the second column of the table above
            for i in range(1, len(pt_running_bal) - 1):
                if i == 7:
                    pass  # do nothing
                elif pt_running_bal[i - 1][1] == 0.0:
                    rsv_running_bal[i][0] = 0.0
                else:
                    rsv_running_bal[i][0] = round(pt_running_bal[i][0] / pt_running_bal[i - 1][1] * rsv_running_bal[i - 1][1], 2)
                rsv_running_bal[i][1] = rsv_running_bal[i - 1][1] + rsv_running_bal[i][0]

            # fix up the final valution located at index 8 of the table above
            rsv_running_bal[8][0] = round(rsv_running_bal[9][1] - rsv_running_bal[7][1], 2)
            rsv_running_bal[8][1] = round(rsv_running_bal[8][0] + rsv_running_bal[7][1], 2)

            # make sure that the ending balance recalculates
            if round(rsv_running_bal[8][1], 2) != round(rsv_running_bal[9][1], 2):
                raise ValueError(f'Ending reserve balance for patient {pt["number"]} does not recalculate.')

            # add the reserve activity to the patient's record
            pt['Rsv: Charges'] = rsv_running_bal[1][0]
            pt['Rsv: Admin Adj'] = rsv_running_bal[2][0]
            pt['Rsv: Bad Debt WO'] = rsv_running_bal[3][0]
            pt['Rsv: Charity Adj'] = rsv_running_bal[4][0]
            pt['Rsv: Contractual Adj'] = rsv_running_bal[5][0]
            pt['Rsv: Denail WO'] = rsv_running_bal[6][0]
            pt['Rsv: Releases'] = rsv_running_bal[7][0]
            pt['Rsv: Valuation'] = rsv_running_bal[8][0]

            if pt['Rsv: Beginning'] < 0.0 and pt['Rsv: Ending'] == 0.0 and pt['Receipts/Refunds'] < 0.0 and pt['Rsv: Valuation'] > 0.0:
                pt['Rsv: Releases'] = pt['Rsv: Valuation']
                pt['Rsv: Valuation'] = 0.0

        pass

    def add_descriptions(self, pt_accts: list[dict]) -> tuple:

        # group the accounts into three categories
        for pt_acct in pt_accts:

            bd = pt_acct['Bad Debt WO']
            beg_rsv = pt_acct['Rsv: Beginning']
            beg_net = pt_acct['Begin Bal'] + beg_rsv
            pay = pt_acct['Receipts/Refunds']
            chg = pt_acct['Charges']
            end_net = pt_acct['Ending Bal'] + pt_acct['Rsv: Ending']

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
                if abs(pay) > (beg_net + chg + pt_acct['Rsv: Charges']):
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

            pt_acct['Description'] = desc

        pass

    def write_to_file(self, output_file: str, pt_accts: list[dict]) -> None:
        descriptors = [
            {
                'table_headers': [h for h in pt_accts[0].keys()],
                'table_rows': pt_accts,
                'table_name': 'PT_ACCT_ROLL',
                'sheet_name': 'Pt Acct Roll-forward'
            }
        ]
        new_wb_with_tables(output_file, descriptors)

    def compile(self, facility_name: str, input_file: str, output_file: str) -> None:
        pt_accts = self.load_file(input_file)
        self.add_reserve_activity(pt_accts)
        self.add_descriptions(pt_accts)
        self.write_to_file(output_file, pt_accts)
