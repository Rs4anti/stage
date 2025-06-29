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
  let gdprMap = {}; // ora oggetto
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

  // Popola i campi principali
  document.getElementById('groupTypeSelect').value = groupType || 'CPPS';

   // Mostra/Nasconde campi specifici in base al tipo selezionato
  toggleCPPNFields();

  document.getElementById('workflowTypeSelect').value = workflowType || 'sequence';
  document.getElementById('groupDescription').value = description || '';
  document.getElementById('groupName').value = name || '';
  document.getElementById('singleActor').value = singleActor || detectGroupActors(element)[0] || '';
  document.getElementById('actorsInvolved').value = actors || detectGroupActors(element).join(', ');

 

  // 🧩 Popola i campi GDPR dinamici
  const gdprContainer = document.getElementById('gdprMapContainer');
  gdprContainer.innerHTML = '';
  if (gdprMap && typeof gdprMap === 'object') {
    Object.entries(gdprMap).forEach(([actor, role]) => addGdprRow(actor, role));
  }

  // Popola gli endpoint
  const epContainer = document.getElementById('endpointsContainer');
  epContainer.innerHTML = '';
  endpoints.forEach(ep => addEndpointRow(ep.method, ep.url));

  // Mostra la modale
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
  const div = document.createElement('div');
  div.classList.add('d-flex', 'mb-2', 'gap-2');

  div.innerHTML = `
    <input type="text" class="form-control form-control-sm" placeholder="Actor" value="${actor}">
    <input type="text" class="form-control form-control-sm" placeholder="Role (e.g., Controller)" value="${role}">
    <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(div);
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



function detectGroupActors(groupElement) {
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const canvas = bpmnModeler.get('canvas');
  const groupBBox = canvas.getAbsoluteBBox(groupElement);

  const lanes = elementRegistry.filter(el => el.type === 'bpmn:Lane');

  const intersecting = lanes.filter(lane => {
    const laneBBox = canvas.getAbsoluteBBox(lane);
    return (
      groupBBox.x < laneBBox.x + laneBBox.width &&
      groupBBox.x + groupBBox.width > laneBBox.x &&
      groupBBox.y < laneBBox.y + laneBBox.height &&
      groupBBox.y + groupBBox.height > laneBBox.y
    );
  });

  return intersecting.map(lane => lane.businessObject.name);
}
