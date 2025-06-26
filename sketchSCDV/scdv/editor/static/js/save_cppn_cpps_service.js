function saveGroupClassification() {
  const modeling = bpmnModeler.get('modeling');
  const moddle = bpmnModeler.get('moddle');

  const type = document.getElementById('groupTypeSelect').value;
  const name = document.getElementById('groupName').value.trim();
  const description = document.getElementById('groupDescription').value.trim();
  const workflowType = document.getElementById('workflowTypeSelect').value;
  const actors = document.getElementById('actorsInvolved').value.trim();
  const gdprMap = document.getElementById('gdprMap').value.trim();

  const bo = currentElement.businessObject;

  // 🔧 Ensure extensionElements exists
  if (!bo.extensionElements) {
    bo.extensionElements = moddle.create('bpmn:ExtensionElements', { values: [] });
  }

  // 🔍 Check if extension already exists
  let ext = bo.extensionElements.values.find(e => e.$type === 'custom:GroupExtension');
  if (!ext) {
    ext = moddle.create('custom:GroupExtension', {});
    bo.extensionElements.values.push(ext);
  }

  // 🧠 Set base data
  ext.groupType = type;
  ext.name = name;
  ext.description = description;
  ext.workflowType = workflowType;

  // 🟧 CPPN-specific fields
  if (type === 'CPPN') {
    ext.actors = actors;
    ext.gdprMap = gdprMap;
  } else {
    ext.actors = '';
    ext.gdprMap = '';
  }

  // 📦 Save list of members (task IDs) inside the group (optional)
  ext.members = detectGroupMembers(currentElement).join(', ');

  // 🖍️ Color feedback
  modeling.setColor(currentElement, {
    stroke: type === 'CPPN' ? '#0000aa' : '#007700',
    fill: type === 'CPPN' ? '#e0e8ff' : '#e6ffe6'
  });

  // 📝 Update name
  modeling.updateProperties(currentElement, {
    name: name
  });

  // ✅ Close modal
  bootstrap.Modal.getInstance(document.getElementById('groupTypeModal')).hide();
}



function toggleCPPNFields() {
  const type = document.getElementById('groupTypeSelect').value;
  const cppnFields = document.getElementById('cppnFields');
  cppnFields.style.display = type === 'CPPN' ? 'block' : 'none';
}


// TODO: verifica funzionamento! rilevazione automatica se cppn o cpps
function detectGroupActors(groupElement) {
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const graphicsFactory = bpmnModeler.get('graphicsFactory');
  const groupShape = graphicsFactory.getShape(groupElement.id);
  const groupBBox = groupShape.getBBox();

  const lanes = elementRegistry.filter(el => el.type === 'bpmn:Lane');

  const intersectingLanes = lanes.filter(lane => {
    const laneBBox = graphicsFactory.getShape(lane.id).getBBox();
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
  const elementRegistry = bpmnModeler.get('elementRegistry');
  const graphicsFactory = bpmnModeler.get('graphicsFactory');
  const groupBBox = graphicsFactory.getShape(groupElement.id).getBBox();

  const taskLike = elementRegistry.filter(el =>
    el.type.startsWith('bpmn:') && (
      el.type === 'bpmn:Task' ||
      el.type === 'bpmn:SubProcess' ||
      el.type === 'bpmn:CallActivity'
    )
  );

  return taskLike
    .filter(el => {
      const shape = graphicsFactory.getShape(el.id);
      return doBoundingBoxesIntersect(groupBBox, shape.getBBox());
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

