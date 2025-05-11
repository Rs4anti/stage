async function saveAtomicService() {

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