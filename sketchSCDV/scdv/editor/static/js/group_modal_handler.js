function openGroupClassificationForm(element) {
  if (!element || !element.businessObject) return;

  currentElement = element;
  const bo = element.businessObject;

  let groupType = '';
  let name = '';
  let description = '';
  let workflowType = '';
  let singleActor = '';
  let actors = '';
  let gdprMap = {};
  let endpoints = [];

  // Estrai eventuale estensione esistente
  if (bo.extensionElements?.values?.length) {
    const ext = bo.extensionElements.values.find(e => e.$type === 'custom:GroupExtension');
    if (ext) {
      groupType = ext.groupType || '';
      name = ext.name || '';
      description = ext.description || '';
      workflowType = ext.workflowType || '';
      singleActor = ext.actor || '';
      actors = ext.actors || '';
      gdprMap = ext.gdprMap || {};
      endpoints = ext.endpoints || [];
    }
  }

  // Se è un nuovo gruppo senza estensioni salvate
  if (!bo.extensionElements?.values?.length) {
    const detectedParticipants = detectGroupParticipants(element);

    // CPPN: imposta attori e mappa GDPR
    if ((groupType || 'CPPS') === 'CPPN') {
      if (detectedParticipants.length > 0) {
        actors = detectedParticipants.join(', ');
        gdprMap = {};
        detectedParticipants.forEach(actor => {
          gdprMap[actor] = ''; // ruoli da compilare
        });
      }
      workflowType = 'sequence';
    }

    // CPPS: imposta attore singolo se unico rilevato
    if ((groupType || 'CPPS') === 'CPPS' && detectedParticipants.length === 1) {
      singleActor = detectedParticipants[0];
    }
  }

  // Popola i campi base
  document.getElementById('groupTypeSelect').value = groupType || 'CPPS';
  toggleCPPNFields();
  document.getElementById('workflowTypeSelect').value = workflowType || 'sequence';
  document.getElementById('groupDescription').value = description || '';
  document.getElementById('groupName').value = name || '';
  document.getElementById('singleActor').value = singleActor || '';
  document.getElementById('actorsInvolved').value = actors || detectGroupParticipants(element).join(', ');
  document.getElementById('singleActor').readOnly = true;
  document.getElementById('actorsInvolved').readOnly = true;

  // Popola GDPR Mapping (attori già noti, ruoli da inserire)
  // Popola GDPR Mapping usando actorsInvolved
const gdprNote = document.getElementById('gdprNote');
populateGdprMappingFromActorsInvolved();

if ((groupType || 'CPPS') === 'CPPN' && gdprNote) {
  gdprNote.style.display = 'inline';
} else if (gdprNote) {
  gdprNote.style.display = 'none';
}


  // Popola endpoint CPPS
  const epContainer = document.getElementById('endpointsContainer');
  epContainer.innerHTML = '';
  endpoints.forEach(ep => addEndpointRow(ep.method, ep.url));

  // Mostra modale
  const modal = new bootstrap.Modal(document.getElementById('groupTypeModal'));
  modal.show();
}



function addEndpointRow(method = '', url = '') {
  const container = document.getElementById('endpointsContainer');
  const div = document.createElement('div');
  div.classList.add('d-flex', 'mb-2', 'gap-2');

  div.innerHTML = `
    <select class="form-select form-select-sm" style="width: 100px;">
      <option value="GET" ${method === 'GET' ? 'selected' : ''}>GET</option>
      <option value="POST" ${method === 'POST' ? 'selected' : ''}>POST</option>
      <option value="PUT" ${method === 'PUT' ? 'selected' : ''}>PUT</option>
      <option value="DELETE" ${method === 'DELETE' ? 'selected' : ''}>DELETE</option>
    </select>
    <input type="text" class="form-control form-control-sm" placeholder="Endpoint URL" value="${url}">
    <button class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(div);
}

function addGdprRow(actor = '', role = '') {
  const container = document.getElementById('gdprMapContainer');
  const row = document.createElement('div');
  row.classList.add('d-flex', 'mb-2', 'gap-2');

  row.innerHTML = `
    <input type="text" class="form-control form-control-sm bg-light text-muted" value="${actor}" readonly>
    <input type="text" class="form-control form-control-sm" placeholder="Role (e.g., Controller)" value="${role}">
  `;

  container.appendChild(row);
}




function toggleCPPNFields() {
  const type = document.getElementById('groupTypeSelect').value;

  const cppnFields = document.getElementById('cppnFields');
  const cppsActorField = document.getElementById('cppsActorField');
  const cppsEndpoints = document.getElementById('cppsEndpoints'); // aggiunto

  if (cppnFields && cppsActorField && cppsEndpoints) {
    if (type === 'CPPN') {
      cppnFields.style.display = 'block';
      cppsActorField.style.display = 'none';
      cppsEndpoints.style.display = 'none'; // nasconde se non CPPS
    } else {
      cppnFields.style.display = 'none';
      cppsActorField.style.display = 'block';
      cppsEndpoints.style.display = 'block'; // mostra se CPPS
    }
  }
}



function detectGroupParticipants(groupElement) {
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const canvas = bpmnModeler.get('canvas');
  const groupBBox = canvas.getAbsoluteBBox(groupElement);

  const participants = elementRegistry.filter(el => el.type === 'bpmn:Participant');

  const intersecting = participants.filter(part => {
    const partBBox = canvas.getAbsoluteBBox(part);
    return (
      groupBBox.x < partBBox.x + partBBox.width &&
      groupBBox.x + groupBBox.width > partBBox.x &&
      groupBBox.y < partBBox.y + partBBox.height &&
      groupBBox.y + groupBBox.height > partBBox.y
    );
  });

  return intersecting.map(getParticipantName);
}


function getParticipantName(element) {
  return element.businessObject.name || '(nessun nome)';
}


function populateGdprMappingFromActorsInvolved() {
  const gdprContainer = document.getElementById('gdprMapContainer');
  gdprContainer.innerHTML = '';

  const raw = document.getElementById('actorsInvolved').value;
  const actors = raw.split(',').map(a => a.trim()).filter(a => a.length > 0);

  actors.forEach(actor => addGdprRow(actor, ''));
}
