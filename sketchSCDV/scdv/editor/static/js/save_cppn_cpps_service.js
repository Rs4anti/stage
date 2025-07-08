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

    // ✅ Se sto salvando un CPPS, verifico se è annidato in un altro CPPS
  if (groupType === 'CPPS') {
    const parentGroup = findParentGroup(currentElement);
    if (parentGroup) {
      console.log("↪️ Il gruppo è annidato dentro:", parentGroup.id);

      const csrftoken = getCookie('csrftoken');

      try {
        const res = await fetch(`/editor/api/add-nested-cpps/${parentGroup.id}/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
          },
          body: JSON.stringify({ nested_id: currentElement.id })
        });

        const resJson = await res.json();
        if (res.ok) {
          console.log("✅ nested_cpps aggiornato per", parentGroup.id);
        } else {
          console.warn("❌ Errore aggiornamento nested_cpps:", resJson.error);
        }
      } catch (err) {
        console.error("❌ Errore fetch nested_cpps:", err.message);
      }
    }
  }

  bootstrap.Modal.getInstance(document.getElementById('groupTypeModal')).hide();
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

  // Funzione: inclusione stretta
  const isStrictlyInside = (inner, outer) =>
    inner.x >= outer.x &&
    inner.y >= outer.y &&
    inner.x + inner.width <= outer.x + outer.width &&
    inner.y + inner.height <= outer.y + outer.height;

  // Recupera i task
  const taskLike = elementRegistry.filter(el =>
    el.type === 'bpmn:Task' ||
    el.type === 'bpmn:SubProcess' ||
    el.type === 'bpmn:CallActivity'
  );

  // Recupera i gruppi annidati
  const allGroups = elementRegistry.filter(el => el.type === 'bpmn:Group');
  const nestedCPPS = allGroups
    .filter(el => el.id !== groupElement.id && isStrictlyInside(canvas.getAbsoluteBBox(el), groupBBox));

  const nestedBBoxes = nestedCPPS.map(el => canvas.getAbsoluteBBox(el));

  const atomicMembers = taskLike
    .filter(el => {
      const elBBox = canvas.getAbsoluteBBox(el);

      // Deve essere completamente dentro il group principale
      if (!isStrictlyInside(elBBox, groupBBox)) return false;

      // NON deve essere dentro uno dei gruppi annidati
      for (const nestedBBox of nestedBBoxes) {
        if (isStrictlyInside(elBBox, nestedBBox)) return false;
      }

      return true;
    })
    .map(el => el.id);

  return {
    atomicMembers,
    nestedCPPS: nestedCPPS.map(el => el.id)
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

