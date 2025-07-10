export default {
  __init__: ['customContextPad'],
  customContextPad: ['type', CustomContextPadProvider]
};

function CustomContextPadProvider(config, contextPad, modeling, translate) {
  contextPad.registerProvider(this);

  let itemToDelete = null;
  let itemTypeToDelete = '';

  // Collega listener al bottone "Elimina" solo quando DOM pronto
  window.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirmDeleteItemBtn');
    const modalEl = document.getElementById('deleteItemModal');

    if (confirmBtn && modalEl) {
      confirmBtn.addEventListener('click', function () {
        if (!itemToDelete) return;

        modeling.removeElements([itemToDelete]);

        let url = '';
        if (itemTypeToDelete === 'group') {
          url = `/editor/api/delete_group/${itemToDelete.id}/`;
        } else if (itemTypeToDelete === 'atomic') {
          url = `/editor/api/delete-atomic/${itemToDelete.id}/`;
        }

        fetch(url, {
          method: 'DELETE',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).then(response => {
          if (!response.ok) {
            console.error(`Errore eliminazione ${itemTypeToDelete} ${itemToDelete.id}`);
          }
        }).catch(error => {
          console.error('Errore di rete:', error);
        });

        bootstrap.Modal.getInstance(modalEl).hide();
        itemToDelete = null;
        itemTypeToDelete = '';
      });
    }
  });

  this.getContextPadEntries = function (element) {
    const actions = {};

    actions['delete'] = {
      group: 'edit',
      className: 'bpmn-icon-trash',
      title: element.type === 'bpmn:Group' ? translate('Delete group and metadata') : translate('Delete atomic service'),
      action: {
        click: function () {
          const typeEl = document.getElementById('deleteItemType');
          const idEl = document.getElementById('deleteItemId');
          const modalEl = document.getElementById('deleteItemModal');

          if (!typeEl || !idEl || !modalEl) {
            console.warn('Modale non trovata nel DOM');
            return;
          }

          itemToDelete = element;
          itemTypeToDelete = element.type === 'bpmn:Group' ? 'group' : 'atomic';

          typeEl.innerText = itemTypeToDelete === 'group' ? 'gruppo' : 'servizio atomico';
          idEl.innerText = element.id;

          new bootstrap.Modal(modalEl).show();
        }
      }
    };

    return actions;
  };
}

CustomContextPadProvider.$inject = ['config', 'contextPad', 'modeling', 'translate'];

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
