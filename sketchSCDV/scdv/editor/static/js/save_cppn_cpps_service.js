async function saveCompositeService() {
  console.log('Function saveCompositeService called');

  if (!currentElement || currentElement.type !== 'bpmn:Group') {
    alert("No group selected.");
    return;
  }

  const csrftoken = getCookie('csrftoken');

  // 🟨 Raccogli dati dalla modale
  const name = document.getElementById('groupName').value.trim();
  const description = document.getElementById('groupDescription').value.trim();
  const groupType = document.getElementById('groupTypeSelect').value;
  const workflowType = document.getElementById('workflowTypeSelect').value;

  const actor = document.getElementById('singleActor').value.trim();              // CPPS
  const actors = document.getElementById('actorsInvolved').value.trim();          // CPPN
  const gdprMap = document.getElementById('gdprMap').value.trim();
  const properties = document.getElementById('cppsProperties').value.trim();

  // 📌 Endpoints
  const endpointRows = document.querySelectorAll('#endpointsContainer > div');
  const endpoints = Array.from(endpointRows).map(row => {
    const method = row.querySelector('select')?.value || '';
    const url = row.querySelector('input')?.value.trim() || '';
    return { method, url };
  });

  // ✅ Inclusa funzione locale per rilevare i membri
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

  // ✅ Inclusa anche funzione bounding box
  function doBoundingBoxesIntersect(a, b) {
    return (
      a.x < b.x + b.width &&
      a.x + a.width > b.x &&
      a.y < b.y + b.height &&
      a.y + a.height > b.y
    );
  }

  const members = detectGroupMembers(currentElement);
  console.log("Group members:", members);

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

  // 📎 Estensione custom su BPMN
  const moddle = bpmnModeler.get('moddle');
  const modeling = bpmnModeler.get('modeling');

  const extensionElement = moddle.create('custom:GroupExtension', {
    groupType,
    name,
    description,
    workflowType,
    members: members.join(','),
    actor: groupType === 'CPPS' ? actor : '',
    actors: groupType === 'CPPN' ? actors : '',
    gdprMap: groupType === 'CPPN' ? gdprMap : '',
    properties: groupType === 'CPPS' ? properties : '',
    endpoints: groupType === 'CPPS' ? endpoints : []
  });

  const extensionElements = moddle.create('bpmn:ExtensionElements', {
    values: [extensionElement]
  });

  modeling.updateProperties(currentElement, {
    name,
    extensionElements
  });

  // 💾 Invio al backend
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
        actor: groupType === 'CPPS' ? actor : '',
        actors: groupType === 'CPPN' ? actors.split(',').map(s => s.trim()) : [],
        gdpr_map: groupType === 'CPPN' && gdprMap ? JSON.parse(gdprMap) : {},
        properties: groupType === 'CPPS' ? properties : '',
        endpoints: groupType === 'CPPS' ? endpoints : []
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
    alert("Communication error with server.");
  }

  bootstrap.Modal.getInstance(document.getElementById('groupTypeModal')).hide();
}
