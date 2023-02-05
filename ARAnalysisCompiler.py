
import csv


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
        self.data = dict()
    
    def load_file(self, input_file: str) -> list[dict]:
        initial_rows = []
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if not ARAnalysisCompiler.headers.issubset(set(reader.fieldnames)):
                raise ValueError('Input file does not have the correct column headers.')
            for row in reader:
                initial_rows.append({
                    'facility': row['Source Facility'].strip(),
                    'number': int(row['Account Number'].strip()),
                    'beg fc': row['Financial Class Beginning'].strip(),
                    'end fc': row['Financial Class Ending'].strip(),
                    'beg date': row['ATB Date - Min'].strip(),
                    'end date': row['ATB Date - Max'].strip(),
                    'beg bal': float(row['Beginning AR Balance'].strip()),
                    'charges': float(row['Charges'].strip()),
                    'admin': float(row['Admin'].strip()),
                    'bd': float(row['Bad Debt'].strip()),
                    'charity': float(row['Charity'].strip()),
                    'contra': float(row['Contractuals'].strip()),
                    'denials': float(row['Denials'].strip()),
                    'pay': float(row['Payments'].strip()),
                    'end bal': float(row['Ending AR Balance'].strip()),
                    'rsv beg': -float(row['MRA - Estimated Reserve Beginning'].strip()),
                    'rsv end': -float(row['MRA - Estimated Reserve Ending'].strip())
                })
        return initial_rows
    
    def calculate_rsv_activity(self, pt_accts: list[dict]) -> None:
        
        # iterate through all the patient accounts
        for pt in pt_accts:
            
            pt_running_bal = [
                [0.0, pt['beg bal']], # 0
                [pt['charges'], 0.0], # 1
                [pt['admin'], 0.0],   # 2
                [pt['bd'], 0.0],      # 3
                [pt['charity'], 0.0], # 4
                [pt['contra'], 0.0],  # 5
                [pt['denials'], 0.0], # 6
                [pt['pay'], 0.0],     # 7
                [0.0, pt['end bal']], # 8
            ]

            # update the patient account running balance in the second column of the table above
            for i in range(1,len(pt_running_bal)-1):
                pt_running_bal[i][1] = pt_running_bal[i-1][1] + pt_running_bal[i][0]
            
            # make sure that the ending balance recalculates
            if round(pt_running_bal[7][1], 2) != round(pt_running_bal[8][1], 2):
                raise ValueError(f'Ending balance for patient {pt["number"]} does not recalculate.')
            
            rsv_running_bal = [
                [0.0, pt['rsv beg']], # 0
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
            for i in range(1,len(pt_running_bal)-1):
                rsv_running_bal[i][0] = round(pt_running_bal[i][0] / pt_running_bal[i-1][1] * rsv_running_bal[i-1][1], 2)
                rsv_running_bal[i][1] = rsv_running_bal[i-1][1] + rsv_running_bal[i][0]
            
            # fix up the final valution located at index 8 of the table above
            rsv_running_bal[8][0] = round(rsv_running_bal[9][1] - rsv_running_bal[7][1], 2)
            rsv_running_bal[8][1] = round(rsv_running_bal[8][0] + rsv_running_bal[7][1] ,2)
            
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

    def group_accounts_into_themes(self, pt_accts: list[dict]) -> dict[list]:

        # nested function for convenience
        def add_account(self, groups: dict[list], group_name: str, pt_acct: dict) -> None:
            array = groups.get(group_name,None)
            if array:
                array.append(pt_acct)
            else:
                groups[group_name] = [pt_acct]

        def receipts_gt_beg_nbv(pt_acct: dict) -> bool:
            return False
        
        groups = dict()

        for pt_acct in pt_accts:
    
            if receipts_gt_beg_nbv(pt_acct):
                add_account(groups, 'Receipts > Beg NBV', pt_acct)
            elif True:
                pass
            else:
                add_account(groups, 'All other', pt_acct)

        return groups

    def write_to_file(self, output_file: str) -> None:
        pass

    def compile(self, input_file: str, output_file: str) -> None:
        pt_accts = self.load_file(input_file)
        self.calculate_rsv_activity(pt_accts)
        self.group_accounts_into_themes(pt_accts)
        self.write_to_file(output_file)
