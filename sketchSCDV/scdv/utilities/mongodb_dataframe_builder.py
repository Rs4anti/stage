import pandas as pd

class AtomicServiceDataFrameBuilder:

    @staticmethod
    def from_document(doc):
        # Overview dataframe
        overview_data = {
            'task_id': [doc['task_id']],
            'diagram_id': [doc['diagram_id']],
            'name': [doc['name']],
            'atomic_type': [doc['atomic_type']],
            'method': [doc['method']],
            'url': [doc['url']],
            'owner': [doc['owner']]
        }
        overview_df = pd.DataFrame(overview_data)

        # Function to detect type
        def detect_type(value):
            if isinstance(value, bool):
                return 'bool'
            if isinstance(value, int):
                return 'int'
            if isinstance(value, float):
                return 'float'
            if isinstance(value, str):
                val = value.strip()
                if val.lower() in ['true', 'false']:
                    return 'bool'
                try:
                    int(val)
                    return 'int'
                except ValueError:
                    pass
                try:
                    float(val)
                    return 'float'
                except ValueError:
                    pass
                return 'string'
            return 'unknown'

        # Parameters dataframe
        params_rows = []

        for param in doc.get('input', []):
            params_rows.append({
                'task_id': doc['task_id'],
                'param_name': param,
                'param_type': detect_type(param),
                'io_type': 'input'
            })

        for param in doc.get('output', []):
            params_rows.append({
                'task_id': doc['task_id'],
                'param_name': param,
                'param_type': detect_type(param),
                'io_type': 'output'
            })

        params_df = pd.DataFrame(params_rows)

        return overview_df, params_df