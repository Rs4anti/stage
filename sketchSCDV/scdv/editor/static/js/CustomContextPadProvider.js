export default {
  __init__: ['customContextPad'],
  customContextPad: ['type', CustomContextPadProvider]
};

function CustomContextPadProvider(
  config, contextPad, modeling, translate
) {
  contextPad.registerProvider(this);

  this.getContextPadEntries = function (element) {
  const actions = {};

  // ✅ Gestione cancellazione CPPS o CPPN (gruppi)
  if (element.type === 'bpmn:Group') {
    actions['delete'] = {
      group: 'edit',
      className: 'bpmn-icon-trash',
      title: translate('Delete group and metadata'),
      action: {
        click: function () {
          if (confirm(`Eliminare il gruppo ${element.id}?`)) {
            modeling.removeElements([element]);
            fetch(`/editor/api/delete_cppn_cpps/${element.id}`, {
              method: 'DELETE',
              headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
          }
        }
      }
    };
  }

  // ✅ Gestione cancellazione atomic task
  if (element.type === 'bpmn:Task') {
    actions['delete'] = {
      group: 'edit',
      className: 'bpmn-icon-trash',
      title: translate('Delete atomic service'),
      action: {
        click: function () {
          if (confirm(`Eliminare il servizio atomico ${element.id}?`)) {
            modeling.removeElements([element]);
            fetch(`/editor/api/delete-atomic/${element.id}/`, {
              method: 'DELETE',
              headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
          }
        }
      }
    };
  }

  return actions;
};

}

CustomContextPadProvider.$inject = [
  'config',
  'contextPad',
  'modeling',
  'translate'
];

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
