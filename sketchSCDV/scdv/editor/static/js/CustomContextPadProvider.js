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

    if (element.type === 'bpmn:Group') {
      actions['delete'] = {
        group: 'edit',
        className: 'bpmn-icon-trash',
        title: translate('Delete group and metadata'),
        action: {
          click: function () {
            console.log('[CustomContextPad] Cestino cliccato per', element.id);

            if (confirm(`Eliminare il gruppo ${element.id}?`)) {
              modeling.removeElements([element]);

              fetch(`/editor/api/delete_group/${element.id}/`, {
                method: 'DELETE',
                headers: {
                  'X-CSRFToken': getCookie('csrftoken')
                }
              }).then(res => {
                if (res.ok) {
                  alert('✅ Gruppo eliminato');
                } else {
                  alert('❌ Errore eliminazione lato server');
                }
              }).catch(err => {
                alert('❌ Errore fetch: ' + err.message);
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
