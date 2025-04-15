## Running the tests

1. Activate the virtual environment
    ```bash
    source samples/python/.venv/bin/activate
    ```
2. Run the tests
    ```bash
    uv run pytest -v -s tests/test_a2a_spec.py
    ```
**Note** The above assumes that the project root is at samples. When the project root changes,
step 1 might no longer be required.