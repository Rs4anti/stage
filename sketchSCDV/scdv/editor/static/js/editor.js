function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const bpmnModeler = new BpmnJS({
  container: '#canvas',
  moddleExtensions: {
    custom: customModdle
  }
});

window.bpmnModeler = bpmnModeler;

const emptyDiagram = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:custom="http://example.com/custom"
                  id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="false"/>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1"/>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;

async function openDiagram(xml) {
  try {
    await bpmnModeler.importXML(xml);
    bpmnModeler.get('canvas').zoom('fit-viewport');
  } catch (err) {
    console.error('Errore apertura diagramma', err);
  }
}


async function saveDiagram() {
  try {
    const { xml } = await bpmnModeler.saveXML({ format: true });
    console.log(xml);

    const name = prompt("Inserisci un nome per il diagramma:");
    if (!name) return;

    const csrftoken = getCookie('csrftoken');

    const response = await fetch('/editor/api/save-diagram/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({
        name: name,
        xml_content: xml
      })
    });

    const data = await response.json();

    if (response.ok) {
      alert("Diagramma salvato con successo!");
      localStorage.setItem('diagramId', data.id);
      window.diagramId = data.id;  // rende disponibile globalmente
    } else {
      alert("Errore nel salvataggio del diagramma. Risposta backend: \n" + JSON.stringify(data));
    }
  } catch (err) {
    console.error("Errore durante l'esportazione/salvataggio:", err);
  }
}

bpmnModeler.get('eventBus').on('element.click', function (e) {
  const el = e.element;

  if (el && el.type === 'bpmn:Task') {
    openAtomicServiceForm(el);
  }

  if (el && el.type === 'bpmn:Group') {
    console.log('thats a group, lets open groups form');
    openGroupClassificationForm(el);
  }

  loadDetailsFromMongo(el);

});

function resetDiagram() {
  openDiagram(emptyDiagram);
}

$('#save-button').click(saveDiagram);

resetDiagram();


async function loadDetailsFromMongo(element) {
  const bo = element.businessObject;
  const type = element.type;
  const id = bo.id;

  let endpoint = null;
  if (type === 'bpmn:Task') {
    endpoint = `/editor/api/atomic_service/${id}/`;
  } else if (type === 'bpmn:Group') {
    try {
      const res = await fetch(`/editor/api/cppn_service/${id}/`);
      if (res.ok) {
        const data = await res.json();
        return renderDetails(data, 'CPPN');
      }
    } catch (_) {}

    try {
      const res = await fetch(`/editor/api/cpps_service/${id}/`);
      if (res.ok) {
        const data = await res.json();
        return renderDetails(data, 'CPPS');
      }
    } catch (_) {}

    renderNotFound(id);
    return;
  }

  if (endpoint) {
    try {
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error("Not found");
      const data = await res.json();
      renderDetails(data, 'Atomic');
    } catch (err) {
      renderNotFound(id);
    }
  }
}

function renderDetails(data, type) {
  const section = document.querySelector('.details-section');
  section.innerHTML = `<h6>Type: ${type}</h6><ul id="input-list"></ul><h6>Output</h6><ul id="output-list"></ul>`;

  if (data.input_params) {
    data.input_params.forEach(i => {
      const li = document.createElement('li');
      li.textContent = i;
      document.getElementById('input-list').appendChild(li);
    });
  }

  if (data.output_params) {
    data.output_params.forEach(o => {
      const li = document.createElement('li');
      li.textContent = o;
      document.getElementById('output-list').appendChild(li);
    });
  }

  ['name', 'description', 'atomic_type', 'actor', 'actors', 'url', 'method'].forEach(k => {
    if (data[k]) {
      const p = document.createElement('p');
      p.innerHTML = `<strong>${k}:</strong> ${Array.isArray(data[k]) ? data[k].join(', ') : data[k]}`;
      section.appendChild(p);
    }
  });
}

function renderNotFound(id) {
  const section = document.querySelector('.details-section');
  section.innerHTML = `<p class="text-muted">No service found for <code>${id}</code>.</p>`;
}
