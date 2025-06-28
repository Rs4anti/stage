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
  let gdprMap = '';
  let properties = '';
  let endpoints = [];

  if (bo.extensionElements?.values?.length) {
    const ext = bo.extensionElements.values.find(e => e.$type === 'custom:GroupExtension');
    if (ext) {
      groupType = ext.groupType || '';
      name = ext.name || '';
      description = ext.description || '';
      workflowType = ext.workflowType || '';
      singleActor = ext.actor || '';
      actors = ext.actors || '';
      gdprMap = ext.gdprMap || '';
      properties = ext.properties || '';
      endpoints = ext.endpoints || [];
    }
  }

  // Compila i campi nel form
  document.getElementById('groupTypeSelect').value = groupType || 'CPPS';
  document.getElementById('workflowTypeSelect').value = workflowType || 'sequence';
  document.getElementById('groupDescription').value = description || '';
  document.getElementById('groupName').value = name || '';
  document.getElementById('singleActor').value = singleActor || detectGroupActors(element)[0] || '';
  document.getElementById('actorsInvolved').value = actors || detectGroupActors(element).join(', ');
  document.getElementById('gdprMap').value = gdprMap || '';

  toggleCPPNFields();

  // Inizializza gli endpoint
  const container = document.getElementById('endpointsContainer');
  container.innerHTML = '';
  endpoints.forEach(ep => addEndpointRow(ep.method, ep.url));

  const modal = new bootstrap.Modal(document.getElementById('groupTypeModal'));
  modal.show();
}

// Funzione per aggiungere una riga di endpoint dinamicamente
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

// Mostra/nasconde campi specifici a CPPS o CPPN
function toggleCPPNFields() {
  const type = document.getElementById('groupTypeSelect').value;
  const cppnFields = document.getElementById('cppnFields');
  const cppsActorField = document.getElementById('cppsActorField');

  if (cppnFields && cppsActorField) {
    cppnFields.style.display = type === 'CPPN' ? 'block' : 'none';
    cppsActorField.style.display = type === 'CPPS' ? 'block' : 'none';
  }
}

// Esempio semplice di rilevamento attori (lane)
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
