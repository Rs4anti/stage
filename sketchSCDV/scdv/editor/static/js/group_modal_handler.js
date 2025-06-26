function openGroupClassificationForm(element) {
  if (!element || !element.businessObject) return;

  currentElement = element;

  const bo = element.businessObject;

  // Recupera eventuale estensione esistente
  let groupType = '';

  if (bo.extensionElements?.values?.length) {
    const ext = bo.extensionElements.values.find(e => e.$type === 'custom:GroupExtension');
    if (ext) {
      groupType = ext.groupType || '';
    }
  }

  // Imposta valore nel form
  document.getElementById('groupTypeSelect').value = groupType || 'CPPS';

  // Mostra modale
  const modal = new bootstrap.Modal(document.getElementById('groupTypeModal'));
  modal.show();
}
