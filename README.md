# SketchSCDV

Applicativo web basato su **Django** per la modellazione e visualizzazione di **Supply Chain Data View (SCDV)**.  
Consente di disegnare da zero diagrammi della supply chain o importarli da file BPMN di esempio in accordo al [modello proposto](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5166945).

---

## Installazione e Avvio

### 1. Clonare la repository
```bash
git clone https://github.com/Rs4anti/stage
```
oppure scaricare lo **zip** della repo e decomprimerlo.

---

### 2. Posizionarsi nella cartella principale
```bash
cd sketchSCDV
```

---

### 3. Creare (opzionale ma consigliato) un virtual environment python
```bash
python -m venv .venv
```

---

### 4. Attivare il virtual environment
- **Linux/MacOS**:
  ```bash
  source .venv/bin/activate
  ```
- **Windows (PowerShell)**:
  ```bash
  .venv\Scripts\activate
  ```

---

### 5. Installare le dipendenze
```bash
pip install -r requirements.txt
```

---

### 6. Entrare nella directory del progetto
```bash
cd scdv
```

---

### 7. Connessione al database MongoDB
L’applicativo utilizza **MongoDB** tramite la libreria `pymongo`.  
Il client è definito in:

```
sketchSCDV/scdv/utilities/mongodb_handler.py
```

Di default è impostato su:
```python
client = MongoClient("mongodb://localhost:27017/")
```

Assicurarsi che il server **MongoDB** sia attivo sulla propria macchina.

---

### 8. Avviare il server locale Django
```bash
py manage.py runserver
```

- Di default in ascolto su: [http://localhost:8000](http://localhost:8000)  
- Per usare un’altra porta, esempio la 8080:
  ```bash
  py manage.py runserver 8080
  ```

---

### 9. Aprire nel browser
Al seguente indirizzo:
```
http://localhost:8000
```

Si trova l'homepage dell’applicativo.

---

## Utilizzo

- **Creazione da zero**: è possibile disegnare una nuova Supply Chain Data View tramite l’apposita funzione.  
- **Import di un diagramma di esempio**: nella cartella `scdv/examples` è presente un file:

  ```
  paper_diagram_example.bpmn
  ```

  Per importarlo direttamente nell’app per testare le funzionalità.

---
