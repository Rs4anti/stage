async function saveCompositeService() {
    console.log('Function saveCompositeService called');

    if (!currentElement || currentElement.type !== 'bpmn:Group') {
        alert("no group selected.");
        return;
    }

    const csrftoken = getCookie('csrftoken');

    // 🟨 Raccogli dati dalla modale
    const name = document.getElementById('groupName').value.trim();
    const description = document.getElementById('groupDescription').value.trim();
    const groupType = document.getElementById('groupTypeSelect').value;
    const workflowType = document.getElementById('workflowTypeSelect').value;
    const actors = document.getElementById('actorsInvolved').value.trim();
    const gdprMap = document.getElementById('gdprMap').value.trim();

    const members = detectGroupMembers(currentElement);
    console.log("Group member's:", members);

    //TODO: validazione ampliambile
    if (!name) {
        alert("Composite service's name is mandatory!");
        return;
    }

    // 🧠 Salva il diagramma se non esiste ancora
    if (!window.diagramId) {
        const { xml } = await bpmnModeler.saveXML({ format: true });

        const diagramName = prompt("Insert a name for the diagram:");
        if (!diagramName) return;

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

    const moddle = bpmnModeler.get('moddle');
    const modeling = bpmnModeler.get('modeling');

    const extensionElement = moddle.create('custom:GroupExtension', {
        groupType,
        name,
        description,
        workflowType,
        members: members.join(','),
        actors: groupType === 'CPPN' ? actors : '',
        gdprMap: groupType === 'CPPN' ? gdprMap : ''
    });

    const extensionElements = moddle.create('bpmn:ExtensionElements', {
        values: [extensionElement]
    });

    modeling.updateProperties(currentElement, {
        name,
        extensionElements
    });

    // Invia al backend
    try {
        const response = await fetch('/editor/api/save-composite-service/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                diagram_id: window.diagramId,
                group_id: currentElement.id,
                group_type: groupType,
                name,
                description,
                workflow_type: workflowType,
                members,
                actors: actors.split(',').map(s => s.trim()),
                gdpr_map: gdprMap ? JSON.parse(gdprMap) : {}
            })
        });

        const result = await response.json();

        if (response.ok) {
            console.log("Composite service saved successfully!", result);
        } else {
            console.error("Saving error:", result);
            alert("Error saving composite service.");
        }
    } catch (err) {
        console.error("Errore network/API:", err);
        alert("Comunication error with server.");
    }

    bootstrap.Modal.getInstance(document.getElementById('groupTypeModal')).hide();
}



function toggleCPPNFields() {
  const type = document.getElementById('groupTypeSelect').value;
  const cppnFields = document.getElementById('cppnFields');
  cppnFields.style.display = type === 'CPPN' ? 'block' : 'none';
}


// TODO: verifica funzionamento! rilevazione automatica se cppn o cpps
function detectGroupActors(groupElement) {
  console.log('detectGroupActors called');
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const canvas = bpmnModeler.get('canvas');

  // Ottieni bounding box assoluto del gruppo
  const groupBBox = canvas.getAbsoluteBBox(groupElement);

  // Filtra tutte le lane (attori)
  const lanes = elementRegistry.filter(el => el.type === 'bpmn:Lane');

  // Trova le lane che intersecano il gruppo
  const intersectingLanes = lanes.filter(lane => {
    const laneBBox = canvas.getAbsoluteBBox(lane);
    return doBoundingBoxesIntersect(groupBBox, laneBBox);
  });

  return intersectingLanes.map(lane => lane.businessObject.name);
}

function doBoundingBoxesIntersect(a, b) {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}



//TODO: verificare funzionamento 
function detectGroupMembers(groupElement) {
  console.log('detectGroupMembers called');

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
      return doBoundingBoxesIntersect(groupBBox, elBBox);
    })
    .map(el => el.id);
}

function doBoundingBoxesIntersect(a, b) {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}