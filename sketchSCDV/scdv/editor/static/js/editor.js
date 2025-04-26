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
  
  const bpmnModeler = new BpmnJS({
    container: '#canvas',
    moddleExtensions: {
      custom: customModdle
    }
  });
  
  const emptyDiagram = `<?xml version="1.0" encoding="UTF-8"?>
  <bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                    xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                    xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                    xmlns:custom="http://example.com/custom"
                    id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
    <bpmn:process id="Process_1" isExecutable="false"/>
    <bpmndi:BPMNDiagram id="BPMNDiagram_1">
      <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1"/>
    </bpmndi:BPMNDiagram>
  </bpmn:definitions>`;
  
  let diagramId = null;
  let currentElement = null;
  
  async function openDiagram(xml) {
    try {
      await bpmnModeler.importXML(xml);
      bpmnModeler.get('canvas').zoom('fit-viewport');
    } catch (err) {
      console.error('Errore apertura diagramma', err);
    }
  }
  
  async function exportDiagram() {
    try {
      const { xml } = await bpmnModeler.saveXML({ format: true });
      console.log(xml);
  
      const name = prompt("Inserisci un nome per il diagramma:");
      if (!name) return;
  
      const csrftoken = getCookie('csrftoken');
  
      const response = await fetch('/api/save-diagram/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
          name: name,
          xml_content: xml
        })
      });
  
      const data = await response.json();
  
      if (response.ok) {
        alert("Diagramma salvato con successo!");
        localStorage.setItem('diagramId', data.id);
      } else {
        alert("Errore nel salvataggio del diagramma. Risposta backend: \n" + JSON.stringify(data));
      }
    } catch (err) {
      console.error('Errore durante l\'esportazione/salvataggio:', err);
    }
  }
  
  
  
  function openAtomicServiceForm(element) {
    currentElement = element;
    const bo = element.businessObject;
  
    let atomicType = '';
    let inputParams = '';
    let outputParams = '';
    let method = '';
    let url = '';
  
    if (bo.extensionElements && bo.extensionElements.values.length) {
      const customExt = bo.extensionElements.values.find(e => e.$type === 'custom:AtomicExtension');
      if (customExt) {
        atomicType = customExt.atomicType || '';
        inputParams = customExt.inputParams || '';
        outputParams = customExt.outputParams || '';
        method = customExt.method || '';
        url = customExt.url || '';
      }
    }
  
    document.getElementById('serviceName').value = bo.name || '';
    document.getElementById('atomicType').value = atomicType;
    document.getElementById('inputParams').value = inputParams;
    document.getElementById('outputParams').value = outputParams;
    document.getElementById('httpMethod').value = method;
    document.getElementById('serviceUrl').value = url;
  
    new bootstrap.Modal(document.getElementById('atomicServiceModal')).show();
  }
  
  async function saveAtomicService() {

    console.log('Funzione saveAtomicService chiamata');

    if (!currentElement) {
      console.log('⚠️ currentElement è nullo');
      return;
    }
  
    const name = document.getElementById('serviceName').value;
    const atomicType = document.getElementById('atomicType').value;
    const inputParams = document.getElementById('inputParams').value.split(',').map(s => s.trim());
    const outputParams = document.getElementById('outputParams').value.split(',').map(s => s.trim());
    const method = document.getElementById('httpMethod').value;
    const url = document.getElementById('serviceUrl').value;
  
    const csrftoken = getCookie('csrftoken');
  
    if (!diagramId) {
      const { xml } = await bpmnModeler.saveXML({ format: true });
  
      const diagramName = prompt("Prima di salvare l'atomic service, inserisci un nome per il diagramma:");
      if (!diagramName) return;
  
      const diagramResponse = await fetch('/api/save-diagram/', {
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
  
      const diagramData = await diagramResponse.json();
      diagramId = diagramData.id;
    }
  
    const moddle = bpmnModeler.get('moddle');
    const modeling = bpmnModeler.get('modeling');
  
    const extensionElement = moddle.create('custom:AtomicExtension', {
      atomicType,
      inputParams: inputParams.join(', '),
      outputParams: outputParams.join(', '),
      method,
      url
    });
  
    const extensionElements = moddle.create('bpmn:ExtensionElements', {
      values: [extensionElement]
    });
  
    modeling.updateProperties(currentElement, {
      name,
      extensionElements
    });
  
    try {
      const response = await fetch('/api/save-atomic-service/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
          diagram_id: diagramId,
          task_id: currentElement.id,
          name,
          atomic_type: atomicType,
          input_params: inputParams,
          output_params: outputParams,
          method,
          url
        })
      });
  
      const result = await response.json();
      console.log(result);
  
      if (response.ok) {
        console.log("Atomic service salvato con successo!", result);
      } else {
        console.error("Errore salvataggio:", result);
        alert("Errore durante il salvataggio dell'atomic service.");
      }
    } catch (err) {
      console.error("Errore rete/API:", err);
      alert("Errore di comunicazione con il server.");
    }
  
    bootstrap.Modal.getInstance(document.getElementById('atomicServiceModal')).hide();
    window.saveAtomicServiceData = saveAtomicServiceData;
  }
  
  
  bpmnModeler.get('eventBus').on('element.click', function(e) {
    const el = e.element;
    if (el.type === 'bpmn:Task') {
      openAtomicServiceForm(el);
    }
  });
  
  function resetDiagram() {
    openDiagram(emptyDiagram);
  }
  
  $('#save-button').click(exportDiagram);
  resetDiagram();  