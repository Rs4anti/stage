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

    def _infer_type(self, value):
        if isinstance(value, bool):
            return 'Bool'
        if isinstance(value, (int, float)):
            return 'Float' if isinstance(value, float) else 'Int'
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ('true', 'false'):
                return 'Bool'
            try:
                int(v)
                return 'Int'
            except ValueError:
                try:
                    float(v)
                    return 'Float'
                except ValueError:
                    return 'String'
        return 'String'

    def _cast_value(self, value, t):
        try:
            if t == 'Int':
                return int(value)
            if t == 'Float':
                return float(value)
            if t == 'Bool':
                return str(value).lower() == 'true'
            return str(value)
        except Exception:
            raise InvalidTypeError(f"Errore nel cast del valore '{value}' come tipo '{t}'")

    def _validate_and_map(self, records, kind):
        rows = []
        for rec in records:
            name = rec.get('name')
            value = rec.get('value')

            inferred_type = rec.get('type') or self._infer_type(value)
            if inferred_type not in self.ALLOWED_TYPES:
                raise InvalidTypeError(f"{kind}: tipo non valido '{inferred_type}'. Validi: {list(self.ALLOWED_TYPES)}")

            casted_value = self._cast_value(value, inferred_type)
            rows.append({'value': name, 'type': inferred_type})
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
        if self.df_main is None or self.df_input is None or self.df_output is None:
            raise ValueError("I dataframe devono essere creati prima di chiamare get_flatted_wide_table()")

        main_data = self.df_main.iloc[0].to_dict()

        input_names = [f"input_{i+1}" for i in range(len(self.df_input))]
        input_values = list(self.df_input['value']) if not self.df_input.empty else []
        input_types = [f"input_{i+1}_type" for i in range(len(self.df_input))]
        input_value_types = list(self.df_input['type']) if not self.df_input.empty else []

        input_dict = dict(zip(input_names, input_values))
        input_type_dict = dict(zip(input_types, input_value_types))

        output_names = [f"output_{i+1}" for i in range(len(self.df_output))]
        output_values = list(self.df_output['value']) if not self.df_output.empty else []
        output_types = [f"output_{i+1}_type" for i in range(len(self.df_output))]
        output_value_types = list(self.df_output['type']) if not self.df_output.empty else []

        output_dict = dict(zip(output_names, output_values))
        output_type_dict = dict(zip(output_types, output_value_types))

        all_data = {**main_data, **input_dict, **input_type_dict, **output_dict, **output_type_dict}
        flatted_wide_df = pd.DataFrame([all_data])

        return flatted_wide_df
