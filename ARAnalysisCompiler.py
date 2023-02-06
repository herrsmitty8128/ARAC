
import csv
from SpreadsheetTools import new_wb_with_tables


class ARAnalysisCompiler:

    headers = {
        #'Source Facility',
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
        self.data = dict()

    def currency(self, string: str) -> float:
        return float(string.replace("-","0.0").replace("(","-").replace(",","").replace(")","").replace("$",""))

    def load_file(self, input_file: str) -> list[dict]:
        initial_rows = []
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if not ARAnalysisCompiler.headers.issubset(set(reader.fieldnames)):
                raise ValueError('Input file does not have the correct column headers.')
            for row in reader:
                initial_rows.append({
                    # 'facility': row['Source Facility'].strip(),
                    'number': int(row['Account Number'].strip()),
                    'beg fc': row['Financial Class Beginning'].strip(),
                    'end fc': row['Financial Class Ending'].strip(),
                    'beg date': row['ATB Date - Min'].strip(),
                    'end date': row['ATB Date - Max'].strip(),
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

    def calculate_reserve_activity(self, pt_accts: list[dict]) -> None:

        # iterate through all the patient accounts
        for pt in pt_accts:

            pt_running_bal = [
                [0.0, pt['beg bal']],  # 0
                [pt['charges'], 0.0],  # 1
                [pt['admin'], 0.0],   # 2
                [pt['bd'], 0.0],      # 3
                [pt['charity'], 0.0],  # 4
                [pt['contra'], 0.0],  # 5
                [pt['denials'], 0.0],  # 6
                [pt['pay'], 0.0],     # 7
                [0.0, pt['end bal']],  # 8
            ]

            # update the patient account running balance in the second column of the table above
            for i in range(1, len(pt_running_bal) - 1):
                pt_running_bal[i][1] = pt_running_bal[i - 1][1] + pt_running_bal[i][0]

            # make sure that the ending balance recalculates
            if round(pt_running_bal[7][1], 2) != round(pt_running_bal[8][1], 2):
                raise ValueError(f'Ending balance for patient {pt["number"]} does not recalculate.')

            rsv_running_bal = [
                [0.0, pt['rsv beg']],  # 0
                [0.0, 0.0],           # 1 charges
                [0.0, 0.0],           # 2 admin
                [0.0, 0.0],           # 3 bd
                [0.0, 0.0],           # 4 charity
                [0.0, 0.0],           # 5 contra
                [0.0, 0.0],           # 6 denials
                [0.0, 0.0],           # 7 pay
                [0.0, 0.0],           # 8 valuation
                [0.0, pt['rsv end']]  # 9
            ]

            # update the running balance of the reserve in the second column of the table above
            for i in range(1, len(pt_running_bal) - 1):
                if pt['beg bal'] == 0.0:
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
            pt['rsv pay'] = rsv_running_bal[7][0]
            pt['rsv val'] = rsv_running_bal[8][0]

        pass

    def split_into_cagetories(self, pt_accts: list[dict]) -> tuple:

        new_balances = []
        fully_reserved = []
        partial_reserve = []
        credit_balances = []
        zero_balances = []

        # group the accounts into three categories
        for pt_acct in pt_accts:
            beg_bal = pt_acct['beg bal']
            if beg_bal > 0.0:
                if abs(beg_bal + pt_acct['rsv beg']) <= 1.0:
                    fully_reserved.append(pt_acct)
                else:
                    partial_reserve.append(pt_acct)
            elif beg_bal < 0.0:
                credit_balances.append(pt_acct)
            else:
                if pt_acct['charges'] > 0.0:
                    new_balances.append(pt_acct)
                else:
                    zero_balances.append(pt_acct)

        return (new_balances, fully_reserved, partial_reserve, credit_balances, zero_balances)
    
    def apply_new_account_themes(self, new_accts: list[dict]) -> None:
        for pt_acct in new_accts:
            pt_acct['Charges Impact'] = pt_acct['charges'] + pt_acct['rsv charges'] + pt_acct['contra'] + pt_acct['rsv contra']
            pt_acct['Admin Impact'] = pt_acct['admin'] + pt_acct['rsv admin']
            pt_acct['BD Impact'] = pt_acct['bd'] + pt_acct['rsv bd']
            pt_acct['Charity Impact'] = pt_acct['charity'] + pt_acct['rsv charity']
            pt_acct['Denials Impact'] = pt_acct['denials'] + pt_acct['rsv denials']
            pt_acct['Payments Impact'] = pt_acct['pay'] + pt_acct['rsv pay']
            pt_acct['Initial valuation'] = pt_acct['rsv val']
    
    def apply_fully_reserved_themes(self, fully_rsv_accts: list[dict]) -> None:
        for pt_acct in fully_rsv_accts:
            pt_acct['Charges Impact'] = pt_acct['charges'] + pt_acct['rsv charges']
            pt_acct['Admin Impact'] = pt_acct['admin'] + pt_acct['rsv admin']
            pt_acct['BD Impact'] = pt_acct['bd'] + pt_acct['rsv bd']
            pt_acct['Charity Impact'] = pt_acct['charity'] + pt_acct['rsv charity']
            pt_acct['Denials Impact'] = pt_acct['denials'] + pt_acct['rsv denials']
            pt_acct['Payments Impact'] = pt_acct['pay'] + pt_acct['rsv pay']
            if pt_acct['pay'] < 0.0:
                pt_acct['Payments Impact'] += (pt_acct['contra'] + pt_acct['rsv contra'])
            else:
                pt_acct['Charges Impact'] += (pt_acct['contra'] + pt_acct['rsv contra'])

    def apply_partial_reserved_themes(self, part_rsv: list[dict]) -> None:
        for pt_acct in part_rsv:
            pt_acct['Charges Impact'] = pt_acct['charges'] + pt_acct['rsv charges']
            pt_acct['Admin Impact'] = pt_acct['admin'] + pt_acct['rsv admin']
            pt_acct['BD Impact'] = pt_acct['bd'] + pt_acct['rsv bd']
            pt_acct['Charity Impact'] = pt_acct['charity'] + pt_acct['rsv charity']
            pt_acct['Denials Impact'] = pt_acct['denials'] + pt_acct['rsv denials']
            pt_acct['Payments Impact'] = pt_acct['pay'] + pt_acct['rsv pay']
            if pt_acct['pay'] < 0.0:
                pt_acct['Payments Impact'] += (pt_acct['contra'] + pt_acct['rsv contra'])
            else:
                pt_acct['Charges Impact'] += (pt_acct['contra'] + pt_acct['rsv contra'])
            

    def apply_credit_balance_themes(self, credit_bal_accts: list[dict]) -> None:
        for pt_acct in credit_bal_accts:
            pt_acct['Admin Impact'] = pt_acct['admin'] + pt_acct['rsv admin']
            pt_acct['BD Impact'] = pt_acct['bd'] + pt_acct['rsv bd']
            pt_acct['Charity Impact'] = pt_acct['charity'] + pt_acct['rsv charity']
            pt_acct['Denials Impact'] = pt_acct['denials'] + pt_acct['rsv denials']
            if pt_acct['charges'] == 0.0 and pt_acct['pay'] != 0.0:
                pt_acct['Charges Impact'] = 0.0
                pt_acct['Payments Impact'] = pt_acct['pay'] + pt_acct['rsv pay'] + pt_acct['contra'] + pt_acct['rsv contra']
            elif pt_acct['charges'] != 0.0 and pt_acct['pay'] == 0.0:
                pt_acct['Charges Impact'] = pt_acct['charges'] + pt_acct['contra'] + pt_acct['rsv contra']
                pt_acct['Payments Impact'] = 0.0
            elif pt_acct['charges'] == 0.0 and pt_acct['pay'] == 0.0:
                pt_acct['Charges Impact'] = 0.0
                pt_acct['Payments Impact'] = 0.0
            else:
                # charges and payments
                pass

    def apply_zero_balance_themes(self, zero_balances: list[dict]) -> None:
        for pt_acct in zero_balances:
            pt_acct['Admin Impact'] = pt_acct['admin'] + pt_acct['rsv admin']
            pt_acct['BD Impact'] = pt_acct['bd'] + pt_acct['rsv bd']
            pt_acct['Charity Impact'] = pt_acct['charity'] + pt_acct['rsv charity']
            pt_acct['Denials Impact'] = pt_acct['denials'] + pt_acct['rsv denials']

    def write_to_file(self, output_file: str, new: list[dict], fully: list[dict], partial: list[dict], credit: list[dict], zero: list[dict]) -> None:
        descriptors = [
            {
                'table_headers': [h for h in new[0].keys()],
                'table_rows': new,
                'table_name': 'NEW_ACCTS',
                'sheet_name': 'New Accts'
            },
            {
                'table_headers': [h for h in fully[0].keys()],
                'table_rows': fully,
                'table_name': 'FULLY_RSV_ACCTS',
                'sheet_name': 'Fully Rsv Accts'
            },
            {
                'table_headers': [h for h in partial[0].keys()],
                'table_rows': partial,
                'table_name': 'PART_RSV_ACCTS',
                'sheet_name': 'Partial Rsv Accts'
            },
            {
                'table_headers': [h for h in credit[0].keys()],
                'table_rows': credit,
                'table_name': 'CREDIT_BAL_ACCTS',
                'sheet_name': 'Credit Bal Accts'
            },
            {
                'table_headers': [h for h in zero[0].keys()],
                'table_rows': zero,
                'table_name': 'ZERO_BAL_ACCTS',
                'sheet_name': 'Zero Bal Accts'
            }
        ]
        new_wb_with_tables(output_file, descriptors)

    def compile(self, facility_name: str, input_file: str, output_file: str) -> None:
        pt_accts = self.load_file(input_file)
        self.calculate_reserve_activity(pt_accts)
        new, fully, partial, credit, zero = self.split_into_cagetories(pt_accts)
        del pt_accts
        self.apply_new_account_themes(new)
        self.apply_fully_reserved_themes(fully)
        self.apply_partial_reserved_themes(partial)
        self.apply_credit_balance_themes(credit)
        self.apply_zero_balance_themes(zero)
        self.write_to_file(output_file, new, fully, partial, credit, zero)
