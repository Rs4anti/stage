export default {
  __init__: ['customContextPad'],
  customContextPad: ['type', CustomContextPadProvider]
};

function CustomContextPadProvider(config, contextPad, modeling, translate) {
  contextPad.registerProvider(this);

  let itemToDelete = null;
  let itemTypeToDelete = '';

  window.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirmDeleteItemBtn');
    const modalEl = document.getElementById('deleteItemModal');

    if (confirmBtn && modalEl) {
      confirmBtn.addEventListener('click', function () {
        if (!itemToDelete) return;

        let deleteUrl = '';
        if (itemTypeToDelete === 'group') {
          deleteUrl = `/editor/api/delete_group/${itemToDelete.id}/`;
        } else if (itemTypeToDelete === 'atomic') {
          deleteUrl = `/editor/api/delete-atomic/${itemToDelete.id}/`;
        }

        modeling.removeElements([itemToDelete]);

        fetch(deleteUrl, {
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
      title: translate('Delete service'),
      action: {
        click: function () {
          const typeEl = document.getElementById('deleteItemType');
          const idEl = document.getElementById('deleteItemId');
          const nameEl = document.getElementById('deleteItemName');
          const descEl = document.getElementById('deleteItemDescription');
          const modalEl = document.getElementById('deleteItemModal');

          if (!typeEl || !idEl || !nameEl || !descEl || !modalEl) {
            console.warn('Modale non trovata nel DOM');
            return;
          }

          itemToDelete = element;

          if (element.type === 'bpmn:Task') {
            itemTypeToDelete = 'atomic';
            typeEl.innerText = 'atomic service';
            idEl.innerText = element.id;

            fetch(`/editor/api/atomic_service/${element.id}/`)
              .then(response => {
                if (!response.ok) {
                  throw new Error(`Atomic non trovato (${response.status})`);
                }
                return response.json();
              })
              .then(data => {
                nameEl.innerText = data.name || '(senza nome)';
                descEl.innerText = data.atomic_type || '(nessuna descrizione)';
                new bootstrap.Modal(modalEl).show();
              })
              .catch(error => {
                console.error('Errore recupero dettagli atomic:', error);
                nameEl.innerText = '(errore recupero)';
                descEl.innerText = error.message;
                new bootstrap.Modal(modalEl).show();
              });

          } else if (element.type === 'bpmn:Group') {
            itemTypeToDelete = 'group';
            typeEl.innerText = 'composite service';
            idEl.innerText = element.id;

            // Primo tentativo: CPPS
            fetch(`/editor/api/cpps_service/${element.id}/`)
              .then(response => {
                if (response.ok) {
                  return response.json();
                } else {
                  // Fallback su CPPN
                  console.warn(`CPPS non trovato per ${element.id}, provo CPPN...`);
                  return fetch(`/editor/api/cppn_service/${element.id}/`)
                    .then(res => {
                      if (!res.ok) {
                        throw new Error(`CPPN non trovato (${res.status})`);
                      }
                      return res.json();
                    });
                }
              })
              .then(data => {
                nameEl.innerText = data.name || '(senza nome)';
                descEl.innerText = data.description || '(nessuna descrizione)';
                new bootstrap.Modal(modalEl).show();
              })
              .catch(error => {
                console.error('Errore recupero dettagli gruppo:', error);
                nameEl.innerText = '(errore recupero)';
                descEl.innerText = error.message;
                new bootstrap.Modal(modalEl).show();
              });

          } else {
            console.warn('Tipo elemento non gestito:', element.type);
          }
        }
      }
    };

    return actions;
  };
}

CustomContextPadProvider.$inject = ['config', 'contextPad', 'modeling', 'translate'];

// Funzione per leggere CSRF dai cookie
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
