async function saveAtomicService() {
    console.log('Funzione saveAtomicService chiamata');

    if (!currentElement) {
        console.log('currentElement è nullo');
        return;
    }

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

    if (!diagramId) {
        const { xml } = await bpmnModeler.saveXML({ format: true });

        const diagramName = prompt("Prima di salvare l'atomic service, inserisci un nome per il diagramma:");
        if (!diagramName) return;

        // Salvataggio del diagramma
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
        diagramId = diagramData.id; // Assegniamo il diagramId
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
        // Ora che abbiamo un diagramId valido, possiamo salvare l'atomic service
        const response = await fetch('/api/save-atomic-service/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                diagram_id: diagramId,  // Passiamo il diagramId che ora è valido
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

    const saveAtomicServiceData = {
        name,
        atomic_type: atomicType,
        input_params: inputParams,
        output_params: outputParams,
        method,
        url
    };
    window.saveAtomicServiceData = saveAtomicServiceData;
}



function validateAtomicServiceFields({ name, atomicType, inputParams, outputParams, method, url }) {
    if (name.trim() === '') {
        alert("Il nome del servizio è obbligatorio.");
        return false;
    }

    if (!atomicType.trim()) {
        alert("Il tipo atomico è obbligatorio.");
        return false;
    }

    if (inputParams.length === 0 || inputParams.every(p => p === '')) {
        alert("Inserire almeno un parametro di input.");
        return false;
    }

    if (outputParams.length === 0 || outputParams.every(p => p === '')) {
        alert("Inserire almeno un parametro di output.");
        return false;
    }

    if (!method.trim()) {
        alert("Il metodo HTTP è obbligatorio.");
        return false;
    }

    if (!url.trim() || !/^\/[a-zA-Z0-9_]+$/.test(url)) { 
        alert("L'URL è obbligatorio o non valido. Deve iniziare con '/' e contenere solo lettere, numeri o underscore.");
        return false;
    }
    
    return true;
}