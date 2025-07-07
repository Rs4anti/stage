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

  //Endpoint dinamici (solo CPPS)
  const endpointRows = document.querySelectorAll('#endpointsContainer > div');
  const endpoints = Array.from(endpointRows).map(row => {
    const method = row.querySelector('select')?.value || '';
    const url = row.querySelector('input')?.value.trim() || '';
    return { method, url };
  });

  const {atomicMembers, nestedCPPS} = detectGroupMembers(currentElement);
  console.log("Atomic members:", atomicMembers);
  console.log("Nested cpps:", nestedCPPS);

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
    members: atomicMembers,
    nested_cpps : nestedCPPS,
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

   // Funzione: un elemento è dentro un bbox
  const isInside = (inner, outer) =>
    outer.x < inner.x + inner.width &&
    outer.x + outer.width > inner.x &&
    outer.y < inner.y + inner.height &&
    outer.y + outer.height > inner.y;

  const taskLike = elementRegistry.filter(el =>
    el.type === 'bpmn:Task' ||
    el.type === 'bpmn:SubProcess' ||
    el.type === 'bpmn:CallActivity'
  );

  const allGroups = elementRegistry.filter(el => el.type === 'bpmn:Group');
  const nestedCPPS = allGroups
    .filter(el => el.id !== groupElement.id && isInside(canvas.getAbsoluteBBox(el), groupBBox));

  // Mappa bounding box dei gruppi annidati
  const nestedBBoxes = nestedCPPS.map(el => canvas.getAbsoluteBBox(el));
  const atomicMembers = taskLike
    .filter(el => {
      const elBBox = canvas.getAbsoluteBBox(el);

      // Deve essere nel gruppo principale
      if (!isInside(elBBox, groupBBox)) return false;

      // NON deve essere dentro un gruppo annidato
      for (const nestedBBox of nestedBBoxes) {
        if (isInside(elBBox, nestedBBox)) return false;
      }

      return true;
    })
    .map(el => el.id);

  return {
    atomicMembers,
    nestedCPPS: nestedCPPS.map(el => el.id)
  };
}
