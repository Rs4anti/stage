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

//registro i miei tipi personalizzati definiti in custom-moddle.js
const bpmnModeler = new BpmnJS({
  container: '#canvas', // dove disegno
  moddleExtensions: {
    custom: customModdle
  }
});

window.bpmnModeler = bpmnModeler;

document.addEventListener('DOMContentLoaded', async () => {
  loadAvailableServices();
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');

  if (id) {
    try {
      const res = await fetch(`/viewer/api/${id}/`);
      if (!res.ok) throw new Error("Diagram not found.");

      const data = await res.json();
      await openDiagram(data.xml_content);
      localStorage.setItem('diagramId', data.id);
      window.diagramId = data.id;

      console.log("Modalità modifica attivata per:", data.name);
    } catch (err) {
      console.error("Errore nel caricamento del diagramma:", err);
      alert("❌ Impossible loading diagram to edit it.");
    }
  } else {
    console.log("New diagram (no id in URL)");
    resetDiagram(); // chiamato solo in modalità creazione da zero
  }
});



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
    console.error('Error opening diagram', err);
  }
}


async function saveDiagram() {
  try {
    const { xml } = await bpmnModeler.saveXML({ format: true });
    console.log(xml);

    let diagramId = localStorage.getItem('diagramId');
    const csrftoken = getCookie('csrftoken');

    let url = '/editor/api/save-diagram/';
    let method = 'POST';
    let body = {
      xml_content: xml
    };

    //Verifica se esiste già un diagramma con quell'ID
    if (diagramId) {
      const check = await fetch(`/editor/api/save-diagram/${diagramId}/`, { method: 'GET' });

      if (check.ok) {
        console.log("Diagram already exist → PUT");
        url += `${diagramId}/`;
        method = 'PUT';
      } else {
        console.log("ID saved is not of any diagram → POST");
        diagramId = null;
        localStorage.removeItem('diagramId');
      }
    }

    //Se nuovo, chiedo nome e verifica univocità
    if (!diagramId) {
      const name = prompt("Insert a name for the BPMN diagram:");
      if (!name) return;

      //Verifica se esiste già un diagramma con questo nome
      const nameCheck = await fetch(`/editor/api/check-name/?name=${encodeURIComponent(name)}`);
      if (!nameCheck.ok) {
        alert("Name checking error!");
        return;
      }

      const nameExists = await nameCheck.json();
      if (nameExists.exists) {
        alert("⚠️ A diagram with this name already exist. Choose another name.");
        return;
      }

      body.name = name;
    }

    // Salvataggio
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify(body)
    });

    const responseText = await response.text();
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error("❌ Parsing error JSON:", responseText);
      alert("❌ Server error: not valid reply.");
      return;
    }

    if (response.ok) {
      alert("✅ Diagram saved successfully!");
      localStorage.setItem('diagramId', data.id);
      window.diagramId = data.id;
    } else {
      alert("⚠️ Errore saving:\n" + JSON.stringify(data));
    }
  } catch (err) {
    console.error("❌ Error saving", err);
    alert("❌ Error.");
  }
}


bpmnModeler.get('eventBus').on('element.click', function (e) {
  const el = e.element;

  if (el && el.type === 'bpmn:Task') {
    openAtomicServiceForm(el);
  }

  if (el && el.type === 'bpmn:Group') {
    openGroupClassificationForm(el);
  }

  loadDetailsFromMongo(el);

});

function resetDiagram() {
  localStorage.removeItem('diagramId');
  delete window.diagramId;
  openDiagram(emptyDiagram);
}


$(document).ready(function () {
  $('#save-button1').click(saveDiagram);
  $('#reset-button').click(resetDiagram);
});


resetDiagram();


async function loadDetailsFromMongo(element) {
  const bo = element.businessObject;
  const type = element.type;
  const id = bo.id;

  if (type === 'bpmn:Task') {
    const endpoint = `/editor/api/atomic_service/${id}/`;
    try {
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error("Atomic service not found");
      const data = await res.json();
      renderDetails(data, 'Atomic');
    } catch (err) {
      console.warn(`Atomic not found for ${id}`);
      renderNotFound(id);
    }
    return;
  }

  if (type === 'bpmn:Group') {
    try {
      // Prova CPPN per primo
      const cppnRes = await fetch(`/editor/api/cppn_service/${id}/`);
      if (cppnRes.ok) {
        const cppnData = await cppnRes.json();
        renderDetails(cppnData, 'CPPN');
        openGroupClassificationForm(element, cppnData);
        return;
      }
    } catch (err) {
      console.warn(`Erro fetching CPPN: ${id}`, err);
    }

    try {
      // Poi prova CPPS
      const cppsRes = await fetch(`/editor/api/cpps_service/${id}/`);
      if (cppsRes.ok) {
        const cppsData = await cppsRes.json();
        renderDetails(cppsData, 'CPPS');
        openGroupClassificationForm(element, cppsData);
        return;
      }
    } catch (err) {
      console.warn(`Error fetching CPPS: ${id}`, err);
    }

    // Nessun servizio trovato
    renderNotFound(id);
    return;
  }
}



function renderDetails(data, type) {
  const section = document.querySelector('.details-section');
  section.innerHTML = ''; // reset

  if (type === 'Atomic') {
    renderAtomicDetails(section, data);
  } else if (type === 'CPPN') {
    renderCPPNDetails(section, data);
  } else if (type === 'CPPS') {
    renderCPPSDetails(section, data);
  } else {
    section.innerHTML = '<p class="text-muted">Unknown service type.</p>';
  }
}

function renderAtomicDetails(section, data) {
  const wrapper = document.createElement('div');
  wrapper.className = 'atomic-details-wrapper';

  const title = document.createElement('h5');
  title.className = 'mb-3 fw-bold';
  title.textContent = 'Details: Atomic Service';
  wrapper.appendChild(title);

  const nameP = document.createElement('p');
  nameP.innerHTML = `<strong>Atomic service name:</strong> ${data.name || '-'}`;
  wrapper.appendChild(nameP);

  const ownerP = document.createElement('p');
  ownerP.innerHTML = `<strong>Owner:</strong> ${data.owner || '-'}`;
  wrapper.appendChild(ownerP);


  const row = document.createElement('div');
  row.className = 'd-flex justify-content-between gap-5 flex-wrap';

  // Input column
  const inputCol = document.createElement('div');
  const inputTitle = document.createElement('h6');
  inputTitle.textContent = 'Input:';
  inputCol.appendChild(inputTitle);
  const inputList = document.createElement('ul');
  (data.input_params || []).forEach(i => {
    const li = document.createElement('li');
    li.textContent = `- ${i}`;
    inputList.appendChild(li);
  });
  inputCol.appendChild(inputList);

  // Output column
  const outputCol = document.createElement('div');
  const outputTitle = document.createElement('h6');
  outputTitle.textContent = 'Output:';
  outputCol.appendChild(outputTitle);
  const outputList = document.createElement('ul');
  (data.output_params || []).forEach(o => {
    const li = document.createElement('li');
    li.textContent = `- ${o}`;
    outputList.appendChild(li);
  });
  outputCol.appendChild(outputList);

  // Meta column
  const metaCol = document.createElement('div');
  const metaList = document.createElement('ul');
  ['atomic_type', 'url', 'method'].forEach(k => {
    if (data[k]) {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${k}:</strong> ${data[k]}`;
      metaList.appendChild(li);
    }
  });
  metaCol.appendChild(metaList);

  // Append columns to row
  row.appendChild(inputCol);
  row.appendChild(outputCol);
  row.appendChild(metaCol);

  wrapper.appendChild(row);
  section.innerHTML = '';
  section.appendChild(wrapper);
}

function renderCPPNDetails(section, data) {
  const title = document.createElement('h6');
  title.className = 'text-muted';
  title.textContent = 'CPPN Service';
  section.appendChild(title);

  const fields = ['name', 'description', 'workflow_type'];
  fields.forEach(k => {
    if (data[k]) {
      const p = document.createElement('p');
      p.innerHTML = `<strong>${k}:</strong> ${data[k]}`;
      section.appendChild(p);
    }
  });

  // Actors
  if (Array.isArray(data.actors)) {
    const actorsTitle = document.createElement('h6');
    actorsTitle.textContent = 'Actors';
    section.appendChild(actorsTitle);
    const ul = document.createElement('ul');
    data.actors.forEach(actor => {
      const li = document.createElement('li');
      li.textContent = actor;
      ul.appendChild(li);
    });
    section.appendChild(ul);
  }

  // GDPR Map
  if (data.gdpr_map && typeof data.gdpr_map === 'object') {
    const gdprTitle = document.createElement('h6');
    gdprTitle.textContent = 'GDPR Map';
    section.appendChild(gdprTitle);
    const dl = document.createElement('dl');
    for (const [actor, role] of Object.entries(data.gdpr_map)) {
      const dt = document.createElement('dt');
      dt.textContent = actor;
      const dd = document.createElement('dd');
      dd.textContent = role;
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    section.appendChild(dl);
  }
}

function renderCPPSDetails(section, data) {
  const title = document.createElement('h6');
  title.className = 'text-muted';
  title.textContent = 'CPPS Service';
  section.appendChild(title);

  const fields = ['name', 'description', 'workflow_type', 'actor'];
  fields.forEach(k => {
    if (data[k]) {
      const p = document.createElement('p');
      p.innerHTML = `<strong>${k}:</strong> ${data[k]}`;
      section.appendChild(p);
    }
  });

  // Endpoints
  if (Array.isArray(data.endpoints)) {
    const endpointsTitle = document.createElement('h6');
    endpointsTitle.textContent = 'Endpoints';
    section.appendChild(endpointsTitle);
    const ul = document.createElement('ul');
    data.endpoints.forEach(ep => {
      const li = document.createElement('li');
      li.textContent = `${ep.method || 'GET'} ${ep.url || ''}`;
      ul.appendChild(li);
    });
    section.appendChild(ul);
  }
}



function renderNotFound(id) {
  const section = document.querySelector('.details-section');
  section.innerHTML = `<p class="text-muted">No service found for <code>${id}</code>.</p>`;
}


async function loadAvailableServices() {
  try {
    const res = await fetch('/editor/api/all-services/');
    const data = await res.json();

    const atomicList = document.getElementById('atomicServiceList');
    const cppsList = document.getElementById('cppsServiceList');
    const cppnList = document.getElementById('cppnServiceList');

    // Pulisce prima
    atomicList.innerHTML = '';
    cppsList.innerHTML = '';
    cppnList.innerHTML = '';

    data.atomic.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.onclick = () => renderDetails(service, 'Atomic');
      atomicList.appendChild(li);
    });

    data.cpps.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.onclick = () => renderDetails(service, 'CPPS');
      cppsList.appendChild(li);
    });

    data.cppn.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.onclick = () => renderDetails(service, 'CPPN');
      cppnList.appendChild(li);
    });
  } catch (err) {
    console.error('Error loading services:', err);
  }
}


async function loadAvailableServices() {
  try {
    const res = await fetch('/editor/api/all-services/');
    const data = await res.json();

    const atomicList = document.getElementById('atomicServiceList');
    const cppsList = document.getElementById('cppsServiceList');
    const cppnList = document.getElementById('cppnServiceList');

    // Svuota le liste
    atomicList.innerHTML = '';
    cppsList.innerHTML = '';
    cppnList.innerHTML = '';

    // Atomic services
    data.atomic.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.addEventListener('click', () => {
        renderDetails(service, 'Atomic');
      });
      atomicList.appendChild(li);
    });

    // CPPS services
    data.cpps.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.addEventListener('click', () => {
        renderDetails(service, 'CPPS');
      });
      cppsList.appendChild(li);
    });

    // CPPN services
    data.cppn.forEach(service => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = service.name;
      li.addEventListener('click', () => {
        renderDetails(service, 'CPPN');
      });
      cppnList.appendChild(li);
    });
  } catch (err) {
    console.error('Error loading services:', err);
  }
}
