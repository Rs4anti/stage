import { loadAvailableServices } from './editor.js';

async function saveCompositeService() {
  console.log('Function saveCompositeService called');

  if (!currentElement || currentElement.type !== 'bpmn:Group') {
    alert("No group selected.");
    return;
  }

  const name = document.getElementById('groupName').value.trim();
  const description = document.getElementById('groupDescription').value.trim();
  const groupType = document.getElementById('groupTypeSelect').value;
  const workflowType = document.getElementById('workflowTypeSelect').value;
  const actor = document.getElementById('singleActor')?.value.trim() || '';
  const actors = document.getElementById('actorsInvolved')?.value.trim() || '';

  //GDPR Mapping dinamico
 // GDPR Mapping dinamico (aggiornato per usare <select>)
  const gdprMap = {};
  const gdprMapContainer = document.getElementById('gdprMapContainer');
  [...gdprMapContainer.children].forEach(row => {
  const actorInput = row.querySelector('input');
  const roleSelect = row.querySelector('select');
  const actorName = actorInput?.value.trim();
  const role = roleSelect?.value.trim();
  if (actorName && role) {
    gdprMap[actorName] = role;
  }
});


  //Endpoint dinamici (solo CPPS)
  const endpointRows = document.querySelectorAll('#endpointsContainer > div');
  const endpoints = Array.from(endpointRows).map(row => {
    const method = row.querySelector('select')?.value || '';
    const url = row.querySelector('input')?.value.trim() || '';
    return { method, url };
  });

  const { components } = detectGroupMembers(currentElement);
  console.log("Detected components:", components);


  if (!name) {
    alert("Composite service's name is mandatory!");
    return;
  }

  if (!window.diagramId) {
    const { xml } = await bpmnModeler.saveXML({ format: true });
    const diagramName = prompt("Insert a name for the diagram:");
    if (!diagramName) return;

    const csrftoken = getCookie('csrftoken');
    const response = await fetch('/editor/api/save-diagram/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({
        name: diagramName,
        xml_content: xml
      })
    });

    const result = await response.json();
    window.diagramId = result.id;
  }

  //Prepara payload
  const payload = {
    diagram_id: window.diagramId,
    group_id: currentElement.id,
    name,
    description,
    workflow_type: workflowType,
    components,
  };

  try {
    let result;

    if (groupType === 'CPPN') {
      payload.group_type = 'CPPN';
      payload.actors = actors.split(',').map(s => s.trim());
      payload.gdpr_map = gdprMap;
      result = await saveCPPNService(payload);
    } else {
      payload.group_type = 'CPPS';
      payload.actor = actor;
      payload.endpoints = endpoints;
      result = await saveCPPSService(payload);
    }

    console.log(`${groupType} saved successfully:`, result);
  } catch (err) {
    console.error(`Error saving ${groupType}:`, err);
    alert(`Error saving ${groupType}: ${err.message}`);
  }

  bootstrap.Modal.getInstance(document.getElementById('groupTypeModal')).hide();
  
  await loadAvailableServices();
}

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


async function saveCPPNService(payload) {
  const csrftoken = getCookie('csrftoken');

  const response = await fetch('/editor/api/save-cppn-service/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify(payload)
  });

  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Error saving CPPN');
  return result;
}

async function saveCPPSService(payload) {
  const csrftoken = getCookie('csrftoken');

  const response = await fetch('/editor/api/save-cpps-service/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify(payload)
  });

  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Error saving CPPS');
  return result;
}

function detectGroupMembers(groupElement) {
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const canvas = bpmnModeler.get('canvas');
  const groupBBox = canvas.getAbsoluteBBox(groupElement);

  const isStrictlyInside = (inner, outer) =>
    inner.x >= outer.x &&
    inner.y >= outer.y &&
    inner.x + inner.width <= outer.x + outer.width &&
    inner.y + inner.height <= outer.y + outer.height;

  // === COMPONENTI ===
  const components = [];

  // 1. Atomic services (task-like)
  const taskLike = elementRegistry.filter(el =>
    ['bpmn:Task', 'bpmn:CallActivity', 'bpmn:SubProcess'].includes(el.type)
  );

  taskLike.forEach(el => {
    const bbox = canvas.getAbsoluteBBox(el);
    if (isStrictlyInside(bbox, groupBBox)) {
      components.push({
        id: el.id,
        type: 'Atomic'
      });
    }
  });

  // 2. Gateway
  const gatewayTypes = ['bpmn:ParallelGateway', 'bpmn:ExclusiveGateway', 'bpmn:InclusiveGateway'];
  const gateways = elementRegistry.filter(el => gatewayTypes.includes(el.type));

  gateways.forEach(gw => {
    const gwBox = canvas.getAbsoluteBBox(gw);
    if (!isStrictlyInside(gwBox, groupBBox)) return;

    const outgoingTargets = (gw.outgoing || [])
      .map(flow => flow.target?.id)
      .filter(Boolean);

    components.push({
      id: gw.id,
      type: gw.type.replace('bpmn:', ''),
      targets: outgoingTargets
    });
  });

  // 3. Gruppi annidati (altri CPPS)
  const allGroups = elementRegistry.filter(el => el.type === 'bpmn:Group');
  const nestedCPPS = allGroups
    .filter(el => el.id !== groupElement.id && isStrictlyInside(canvas.getAbsoluteBBox(el), groupBBox))
    .map(el => el.id);

  const nestedComponents = nestedCPPS.map(el => ({
  id: el.id,
  type: 'CPPS'
}));

  
return {
  components: [...components, ...nestedComponents]
};
}



function findParentGroup(innerGroup) {
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const canvas = bpmnModeler.get('canvas');
  const innerBBox = canvas.getAbsoluteBBox(innerGroup);

  const groups = elementRegistry.filter(el =>
    el.type === 'bpmn:Group' && el.id !== innerGroup.id
  );

  return groups.find(g => {
    const outerBBox = canvas.getAbsoluteBBox(g);
    return (
      innerBBox.x >= outerBBox.x &&
      innerBBox.y >= outerBBox.y &&
      innerBBox.x + innerBBox.width <= outerBBox.x + outerBBox.width &&
      innerBBox.y + innerBBox.height <= outerBBox.y + outerBBox.height
    );
  });
}

document.getElementById('save-composite-button')
  .addEventListener('click', saveCompositeService);