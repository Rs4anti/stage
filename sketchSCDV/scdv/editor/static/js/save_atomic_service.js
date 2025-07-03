async function saveAtomicService() {
    console.log('Called function saveAtomicService.');

    if (!currentElement) {
        console.log('currentElement is null');
        return;
    }

    // Recupera il diagramId correttamente
    let diagramId = window.diagramId || localStorage.getItem('diagramId');

    const name = document.getElementById('serviceName').value;
    const atomicType = document.getElementById('atomicType').value;
    const inputParams = document.getElementById('inputParams').value.split(',').map(s => s.trim());
    const outputParams = document.getElementById('outputParams').value.split(',').map(s => s.trim());
    const method = document.getElementById('httpMethod').value;
    const url = document.getElementById('serviceUrl').value;

    if (!validateAtomicServiceFields({ name, atomicType, inputParams, outputParams, method, url })) {
        return;
    }

    const csrftoken = getCookie('csrftoken');

    // Se il diagramId non è ancora salvato o non valido, salva prima il diagramma
    if (!diagramId) {
        const { xml } = await bpmnModeler.saveXML({ format: true });

        const diagramName = prompt("Before saving atomic service, insert a diagram's name:");
        if (!diagramName) return;

        const diagramResponse = await fetch('/editor/api/save-diagram/', {
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
        window.diagramId = diagramId;
        localStorage.setItem('diagramId', diagramId);
    }

    // Aggiunta estensione custom all’elemento BPMN selezionato
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

    // Salvataggio atomic service sul backend
    try {
        const response = await fetch('/editor/api/save-atomic-service/', {
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

        if (response.ok) {
            console.log("✅ Atomic service saved successfully!", result);
        } else {
            console.error("❌ Error saving:", result);
            alert("Error saving atomic service.");
        }
    } catch (err) {
        console.error("❌ Network error/api:", err);
        alert("Comunication server error.");
    }

    // Chiudi il modal
    bootstrap.Modal.getInstance(document.getElementById('atomicServiceModal')).hide();

    // Memorizza dati dell’atomic service per uso futuro
    window.saveAtomicServiceData = {
        name,
        atomic_type: atomicType,
        input_params: inputParams,
        output_params: outputParams,
        method,
        url
    };
}


function validateAtomicServiceFields({ name, atomicType, inputParams, outputParams, method, url }) {
    if (name.trim() === '') {
        alert("Service's name is mandatory.");
        return false;
    }

    if (!atomicType.trim()) {
        alert("Type's name is mandatory.");
        return false;
    }

    if (inputParams.length === 0 || inputParams.every(p => p === '')) {
        alert("Insert at least one input parameter.");
        return false;
    }

    if (outputParams.length === 0 || outputParams.every(p => p === '')) {
        alert("Insert at least one output parameter.");
        return false;
    }

    if (!method.trim()) {
        alert("HTTP method is mandatory.");
        return false;
    }

    if (!url.trim() || !/^\/[a-zA-Z0-9_]+$/.test(url)) {
        alert("URL is mandatory or not valid. Must starts with '/' (only chars, number or underscores allowed)");
        return false;
    }

    return true;
}
