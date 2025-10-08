# SCDV Modeller

Web application based on **Django** for modeling and visualization of
**Supply Chain Data View (SCDV)**.\
It allows creating supply chain diagrams from scratch or importing BPMN
example files according to the [proposed
model](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5166945).

------------------------------------------------------------------------

## Installation and Setup

### 1. Clone the repository

``` bash
git clone https://github.com/Rs4anti/stage
```

or download the repo **zip** file and extract it.

------------------------------------------------------------------------

### 2. Move into the main folder

``` bash
cd sketchSCDV
```

------------------------------------------------------------------------

### 3. Create a Python virtual environment (optional but recommended)

``` bash
python -m venv .venv
```

------------------------------------------------------------------------

### 4. Activate the virtual environment

-   **Linux/MacOS**:

    ``` bash
    source .venv/bin/activate
    ```

-   **Windows (PowerShell)**:

    ``` bash
    .venv\Scripts\activate
    ```

------------------------------------------------------------------------

### 5. Install dependencies

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

### 6. Enter the project directory

``` bash
cd scdv
```

------------------------------------------------------------------------

### 7. Connect to MongoDB

The application uses **MongoDB** through the `pymongo` library.\
The client is defined in:

    sketchSCDV/scdv/utilities/mongodb_handler.py

By default, it is set to:

``` python
client = MongoClient("mongodb://localhost:27017/")
```

Make sure the **MongoDB** server is running locally.

------------------------------------------------------------------------

### 8. Run the Django development server

``` bash
py manage.py runserver
```

-   By default it runs on: <http://localhost:8000>\

-   To use another port, e.g. 8080:

    ``` bash
    py manage.py runserver 8080
    ```

------------------------------------------------------------------------

### 9. Open in the browser

Go to:

    http://localhost:8000

You will find the application homepage.

------------------------------------------------------------------------

## Usage

-   **Create from scratch**: design a new Supply Chain Data View using
    the dedicated function.\

-   **Import an example diagram**: in the `scdv/examples` folder there
    is a file:

        paper_diagram_example.bpmn

    You can import it directly into the app to test functionalities.

------------------------------------------------------------------------
