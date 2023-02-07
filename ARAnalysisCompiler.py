
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
                    'number': int(row['Account Number'].strip()),
                    'beg fc': row['Financial Class Beginning'].strip(),
                    'end fc': row['Financial Class Ending'].strip(),
                    'beg bal': self.currency(row['Beginning AR Balance'].strip()),
                    'charges': self.currency(row['Charges'].strip()),
                    'admin': self.currency(row['Admin'].strip()),
                    'bd': self.currency(row['Bad Debt'].strip()),
                    'charity': self.currency(row['Charity'].strip()),
                    'contra': self.currency(row['Contractuals'].strip()),
                    'denials': self.currency(row['Denials'].strip()),
                    'pay': self.currency(row['Payments'].strip()),
                    'end bal': self.currency(row['Ending AR Balance'].strip()),
                    'rsv beg': -self.currency(row['MRA - Estimated Reserve Beginning'].strip()),
                    'rsv end': -self.currency(row['MRA - Estimated Reserve Ending'].strip())
                })
        return initial_rows

    def add_reserve_activity(self, pt_accts: list[dict]) -> None:

        # iterate through all the patient accounts
        for pt in pt_accts:

            pt_running_bal = [
                [0.0, pt['beg bal']],  # 0
                [pt['charges'], 0.0],  # 1
                [pt['admin'], 0.0],    # 2
                [pt['bd'], 0.0],      # 3
                [pt['charity'], 0.0],  # 4
                [pt['contra'], 0.0],  # 5
                [pt['denials'], 0.0],  # 6
                [pt['pay'], 0.0],      # 7
                [0.0, pt['end bal']],  # 8
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
                [0.0, pt['rsv beg']],  # 0 beginning balance
                [0.0, 0.0],            # 1 charges
                [0.0, 0.0],            # 2 admin
                [0.0, 0.0],            # 3 bd
                [0.0, 0.0],            # 4 charity
                [0.0, 0.0],            # 5 contra
                [0.0, 0.0],            # 6 denials
                [0.0, 0.0],            # 7 releases
                [0.0, 0.0],            # 8 valuation
                [0.0, pt['rsv end']]  # 9 ending balance
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
            pt['rsv charges'] = rsv_running_bal[1][0]
            pt['rsv admin'] = rsv_running_bal[2][0]
            pt['rsv bd'] = rsv_running_bal[3][0]
            pt['rsv charity'] = rsv_running_bal[4][0]
            pt['rsv contra'] = rsv_running_bal[5][0]
            pt['rsv denials'] = rsv_running_bal[6][0]
            pt['rsv release'] = rsv_running_bal[7][0]
            pt['rsv val'] = rsv_running_bal[8][0]

            if pt['rsv beg'] < 0.0 and pt['rsv end'] == 0.0 and pt['pay'] < 0.0 and pt['rsv val'] > 0.0:
                pt['rsv release'] = pt['rsv val']
                pt['rsv val'] = 0.0

        pass

    def add_themes(self, pt_accts: list[dict]) -> tuple:

        # group the accounts into three categories
        for pt_acct in pt_accts:
            beg_bal = pt_acct['beg bal']
            beg_rsv = pt_acct['rsv beg']
            beg_net = beg_bal + beg_rsv
            pay = pt_acct['pay']
            chg = pt_acct['charges']
            end_bal = pt_acct['end bal']
            end_rsv = pt_acct['rsv end']
            end_net = end_bal + end_rsv

            if beg_net > 0.0:  # net debits
                if chg > 0.0:
                    if pay < 0.0:
                        if abs(pay) >= beg_net + chg:
                            if end_net > 0.0:
                                pt_acct['Theme'] = 'Net debit accounts with net receipts > begin bal + charges resulting in a net debit ending balance.'
                            elif end_net < 0.0:
                                pt_acct['Theme'] = 'Net debitaccounts with net receipts > begin bal + charges resulting in a net credit ending balance.'
                            else:
                                pt_acct['Theme'] = 'Net debit accounts with net receipts > begin bal + charges resulting in a net zero ending balance.'
                        else:
                            if end_net > 0.0:
                                pt_acct['Theme'] = 'Net debit accounts with net receipts < begin bal + charges resulting in a net debit ending balance.'
                            elif end_net < 0.0:
                                pt_acct['Theme'] = 'Net debit accounts with net receipts < begin bal + charges resulting in a net credit ending balance.'
                            else:
                                pt_acct['Theme'] = 'Net debit accounts with net receipts < begin bal + charges resulting in a net zero ending balance.'
                    elif pay > 0.0:
                        pt_acct['Theme'] = 'Net debit accounts with net refund'
                    else:
                        pt_acct['Theme'] = 'Net debit accounts - no cash activity.'
                elif chg < 0.0:
                    pt_acct['Theme'] = 'Net debit accounts with charge reversals.'
                else:
                    pt_acct['Theme'] = 'Net debit accounts without charges.'

            elif beg_net < 0.0:  # net credits
                pt_acct['Theme'] = 'Net credit'

            else:  # net 0.0
                if beg_bal == 0.0 and pt_acct['beg fc'] == '':
                    if chg > 0.0:
                        if pay < 0.0:
                            if abs(pay) >= chg:
                                if end_net > 0.0:
                                    pt_acct['Theme'] = 'New accounts with net receipts > charges resulting in a net debit ending balance.'
                                elif end_net < 0.0:
                                    pt_acct['Theme'] = 'New accounts with net receipts > charges resulting in a net credit ending balance.'
                                else:
                                    pt_acct['Theme'] = 'New accounts with net receipts > charges resulting in a net zero ending balance.'
                            else:
                                if end_net > 0.0:
                                    pt_acct['Theme'] = 'New accounts with net receipts < charges resulting in a net debit ending balance.'
                                elif end_net < 0.0:
                                    pt_acct['Theme'] = 'New accounts with net receipts < charges resulting in a net credit ending balance.'
                                else:
                                    pt_acct['Theme'] = 'New accounts with net receipts < charges resulting in a net zero ending balance.'
                        elif pay > 0.0:
                            pt_acct['Theme'] = 'New accounts with net refund'
                        else:
                            pt_acct['Theme'] = 'New accounts - no cash activity.'
                    elif chg < 0.0:
                        pt_acct['Theme'] = 'New accounts with charge reversals.'
                    else:
                        pt_acct['Theme'] = 'New accounts without charges.'
                else:
                    pt_acct['Theme'] = 'Net zero - Other'

        pass

    def write_to_file(self, output_file: str, pt_accts: list[dict]) -> None:
        descriptors = [
            {
                'table_headers': [h for h in pt_accts[0].keys()],
                'table_rows': pt_accts,
                'table_name': 'PT_ACCTS',
                'sheet_name': 'Pt Accts'
            }
        ]
        new_wb_with_tables(output_file, descriptors)

    def compile(self, facility_name: str, input_file: str, output_file: str) -> None:
        pt_accts = self.load_file(input_file)
        self.add_reserve_activity(pt_accts)
        self.add_themes(pt_accts)
        self.write_to_file(output_file, pt_accts)
