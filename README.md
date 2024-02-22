For Windows
```sh
python -m venv venv
cd ./venv/Scripts && activate && cd ../../
python mvn_resolve.py org.yaml:snakeyaml ./pom.xml
```

For Linux
```sh
python3 -m venv .venv
source ./.venv/bin/activate
python3 mvn_resolve.py org.yaml:snakeyaml ./pom.xml
```
