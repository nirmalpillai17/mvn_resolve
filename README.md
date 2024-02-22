For Windows
```sh
python -m venv venv
cd ./venv/Scripts && activate && cd ../../
pip install -r requirements.txt
python mvn_resolve.py org.yaml:snakeyaml ./pom.xml
```

For Linux
```sh
python3 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
python3 mvn_resolve.py org.yaml:snakeyaml ./pom.xml
```
