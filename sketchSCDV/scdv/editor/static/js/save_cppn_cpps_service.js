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

  // ⬇️ GDPR Mapping dinamico
  const gdprMap = {};
  const gdprMapContainer = document.getElementById('gdprMapContainer');
  [...gdprMapContainer.children].forEach(row => {
    const inputs = row.querySelectorAll('input');
    const actorName = inputs[0]?.value.trim();
    const role = inputs[1]?.value.trim();
    if (actorName && role) {
      gdprMap[actorName] = role;
    }
  });

  // ⬇️ Endpoint dinamici (solo CPPS)
  const endpointRows = document.querySelectorAll('#endpointsContainer > div');
  const endpoints = Array.from(endpointRows).map(row => {
    const method = row.querySelector('select')?.value || '';
    const url = row.querySelector('input')?.value.trim() || '';
    return { method, url };
  });

  const members = detectGroupMembers(currentElement);
  console.log("Group members:", members);

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

  // ⬇️ Prepara payload
  const payload = {
    diagram_id: window.diagramId,
    group_id: currentElement.id,
    name,
    description,
    workflow_type: workflowType,
    members
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

  const taskLike = elementRegistry.filter(el =>
    el.type === 'bpmn:Task' ||
    el.type === 'bpmn:SubProcess' ||
    el.type === 'bpmn:CallActivity'
  );

  return taskLike
    .filter(el => {
      const elBBox = canvas.getAbsoluteBBox(el);
      return (
        groupBBox.x < elBBox.x + elBBox.width &&
        groupBBox.x + groupBBox.width > elBBox.x &&
        groupBBox.y < elBBox.y + elBBox.height &&
        groupBBox.y + groupBBox.height > elBBox.y
      );
    })
    .map(el => el.id);
}