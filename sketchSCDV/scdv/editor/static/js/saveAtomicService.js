async function saveAtomicService() {

    if (!validateAtomicServiceForm()) {
        alert("Controlla i campi evidenziati.");
        return;
    }

    const name = document.getElementById('serviceName').value;
    const atomicType = document.getElementById('atomicType').value;
    const inputParams = document.getElementById('inputParams').value.split(',').map(s => s.trim());
    const outputParams = document.getElementById('outputParams').value.split(',').map(s => s.trim());
    const method = document.getElementById('httpMethod').value;
    const url = document.getElementById('serviceUrl').value;

    const csrftoken = getCookie('csrftoken');

      // VALIDAZIONE
    if (!name || !atomicType || inputParams.length === 0 || outputParams.length === 0 || !method || !url) {
        alert("Compila tutti i campi prima di salvare il servizio.");
        return;
    }

    const urlPattern = /^\/[a-zA-Z0-9/_\-\.]*$/;
    if (!urlPattern.test(url)) {
        alert("Inserisci un URL valido (es: /endpoint).");
        return;
    }

    // Se diagramId non è definito, salviamo prima il diagramma
    console.log("Arrivo al check del diagram")
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
    window.saveAtomicServiceData = saveAtomicServiceData;
}


function validateAtomicServiceForm() {
    let isValid = true;
  
    const nameInput = document.getElementById('serviceName');
    const atomicType = document.getElementById('atomicType');
    const inputParams = document.getElementById('inputParams');
    const outputParams = document.getElementById('outputParams');
    const httpMethod = document.getElementById('httpMethod');
    const serviceUrl = document.getElementById('serviceUrl');
  
    const urlPattern = /^\/[a-zA-Z0-9/_\-\.]*$/;
  
    function markInvalid(input, condition, message) {
      const feedback = input.nextElementSibling;
      if (condition) {
        input.classList.add('is-invalid');
        if (feedback && feedback.classList.contains('invalid-feedback')) {
          feedback.textContent = message;
        }
        isValid = false;
      } else {
        input.classList.remove('is-invalid');
      }
    }
  
    const name = nameInput.value.trim();
    markInvalid(nameInput, !name, "Il nome è obbligatorio.");
  
    const inputList = inputParams.value.split(',').map(s => s.trim()).filter(Boolean);
    markInvalid(inputParams, inputList.length === 0, "Almeno un parametro di input è richiesto.");
  
    const outputList = outputParams.value.split(',').map(s => s.trim()).filter(Boolean);
    markInvalid(outputParams, outputList.length === 0, "Almeno un parametro di output è richiesto.");
  
    markInvalid(atomicType, !atomicType.value, "Seleziona un tipo di servizio.");
    markInvalid(httpMethod, !httpMethod.value, "Seleziona un metodo HTTP.");
  
    const url = serviceUrl.value.trim();
    const invalidUrl = !url || !urlPattern.test(url);
    markInvalid(serviceUrl, invalidUrl, "L'endpoint deve iniziare con '/' e non contenere spazi.");
  
    return isValid;
  }
  