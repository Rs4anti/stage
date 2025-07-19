import pandas as pd

class AtomicServiceDataFrameBuilder:

    @staticmethod
    def from_document(doc):
        # DataFrame 1: overview
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

        # DataFrame 2: input/output params
        params_rows = []

        for param in doc.get('input_params', []):
            params_rows.append({
                'task_id': doc['task_id'],
                'param_name': param,
                'param_type': 'string',   # per ora default, in futuro potrai arricchire
                'io_type': 'input'
            })

        for param in doc.get('output_params', []):
            params_rows.append({
                'task_id': doc['task_id'],
                'param_name': param,
                'param_type': 'string',
                'io_type': 'output'
            })

        params_df = pd.DataFrame(params_rows)

        return overview_df, params_df