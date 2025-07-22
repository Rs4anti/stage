import random
import string
import requests
from datetime import datetime

# Funzioni helper
def random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_bool():
    return random.choice([True, False])

def random_float():
    return round(random.uniform(1, 100), 2)

def random_int():
    return random.randint(1, 100)

API_BASE = 'http://localhost:8000/editor/api'

# Template minimo XML per diagramma vuoto
BLANK_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  id="Definitions_{id}"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_{id}" isExecutable="false">
  </bpmn:process>
</bpmn:definitions>'''

# Step 1: crea 3 diagrammi vuoti
diagram_ids = []

for i in range(3):
    diagram_name = f"Test Diagram {datetime.utcnow().isoformat()}"
    diagram_payload = {
        "name": diagram_name,
        "xml_content": BLANK_XML.format(id=random_string(6)),
    }

    try:
        response = requests.post(f"{API_BASE}/save-diagram/", json=diagram_payload)
        if response.status_code in [200, 201]:
            diagram_data = response.json()
            diagram_id = diagram_data.get('_id') or diagram_data.get('id')
            if diagram_id:
                diagram_ids.append(diagram_id)
                print(f"✅ Diagramma creato: {diagram_id}")
            else:
                print(f"⚠️ Nessun ID restituito per diagramma {i}")
        else:
            print(f"❌ Errore creando diagramma {i}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Errore connessione API diagrammi: {e}")

if not diagram_ids:
    print("❌ Nessun diagramma creato, fermo il seeder.")
    exit(1)

# Step 2: genera 20 atomic services random e assegnali ai diagrammi
for i in range(20):
    input_params = [
        random_string(),
        random_bool(),
        random_int(),
        random_float()
    ]
    output_params = [
        random_string(),
        random_bool(),
        random_int()
    ]

    payload = {
        'task_id': f'Activity_{random_string(8)}',
        'atomic_type': random.choice(['collect', 'process&monitor', 'dispatch', 'display']),
        'diagram_id': random.choice(diagram_ids),
        'input_params': [str(v) for v in input_params],
        'output_params': [str(v) for v in output_params],
        'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
        'name': f'as_{i}',
        'url': f'/url{i}',
        'owner': random.choice(['paolo', 'maria', 'giulia', 'luca'])
    }

    try:
        response = requests.post(f"{API_BASE}/save-atomic-service/", json=payload)
        if response.status_code in [200, 201]:
            print(f"✅ [OK] Atomic service {i} salvato.")
        else:
            print(f"⚠️ [WARN] Atomic service {i} non salvato. Status: {response.status_code}, Message: {response.text}")
    except Exception as e:
        print(f"❌ [ERROR] Errore salvando atomic service {i}: {e}")

print("🏁 Seeder completato.")
