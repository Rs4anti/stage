import pandas as pd

class InvalidTypeError(Exception):
    pass

class DataFrameAtomic:
    ALLOWED_TYPES = {'String': 'string', 'Int': 'Int64', 'Float': 'float', 'Bool': 'boolean'}

    def __init__(self, payload):
        self.payload = payload
        self.df_main = None
        self.df_input = None
        self.df_output = None

    def create_main_dataframe(self):
        data = {k: [self.payload[k]] for k in ['diagram_id', 'task_id', 'name', 'atomic_type', 'method', 'url', 'owner']}
        self.df_main = pd.DataFrame(data)
        return self.df_main

    def _validate_and_map(self, records, kind):
        rows = []
        for rec in records:
            name = rec.get('name')
            t = rec.get('type')
            if t not in self.ALLOWED_TYPES:
                raise InvalidTypeError(f"{kind}: tipo non valido '{t}'. Validi: {list(self.ALLOWED_TYPES)}")
            rows.append({'name': name, 'type': t})
        return rows

    def create_io_dataframes(self):
        in_records = self.payload.get('input_params', [])
        out_records = self.payload.get('output_params', [])

        in_valid = self._validate_and_map(in_records, 'input_params')
        out_valid = self._validate_and_map(out_records, 'output_params')

        self.df_input = pd.DataFrame(in_valid).astype({'name': 'string', 'type': 'string'}) if in_valid else pd.DataFrame(columns=['name', 'type'])
        self.df_output = pd.DataFrame(out_valid).astype({'name': 'string', 'type': 'string'}) if out_valid else pd.DataFrame(columns=['name', 'type'])

        return self.df_input, self.df_output

    def get_serialized(self):
        return {
            'main': self.df_main.to_dict(orient='records'),
            'input_params': self.df_input.to_dict(orient='records'),
            'output_params': self.df_output.to_dict(orient='records')
        }
    
    def get_flatted_wide_table(self):
        """
        Restituisce un DataFrame wide: main + input_X + input_X_type + output_X + output_X_type come colonne.
        """
        if self.df_main is None or self.df_input is None or self.df_output is None:
            raise ValueError("I dataframe devono essere creati prima di chiamare get_flatted_wide_table()")

        # Prepara main
        main_data = self.df_main.iloc[0].to_dict()

        # Prepara input columns + types
        input_names = [f"input_{i+1}" for i in range(len(self.df_input))]
        input_values = list(self.df_input['name']) if not self.df_input.empty else []
        input_types = [f"input_{i+1}_type" for i in range(len(self.df_input))]
        input_value_types = list(self.df_input['type']) if not self.df_input.empty else []

        input_dict = dict(zip(input_names, input_values))
        input_type_dict = dict(zip(input_types, input_value_types))

        # Prepara output columns + types
        output_names = [f"output_{i+1}" for i in range(len(self.df_output))]
        output_values = list(self.df_output['name']) if not self.df_output.empty else []
        output_types = [f"output_{i+1}_type" for i in range(len(self.df_output))]
        output_value_types = list(self.df_output['type']) if not self.df_output.empty else []

        output_dict = dict(zip(output_names, output_values))
        output_type_dict = dict(zip(output_types, output_value_types))

        # Merge tutto
        all_data = {**main_data, **input_dict, **input_type_dict, **output_dict, **output_type_dict}

        # Crea DataFrame single-row
        flatted_wide_df = pd.DataFrame([all_data])

        return flatted_wide_df
        