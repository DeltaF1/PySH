<h1>Command Line Arguments</h1>
PySH takes command line arguments in the following format
````
python main.py --name=value
````
The string is lowered, so capitals don't matter

Name | Meaning | Default
-----|-------- | ---------
Port | The port to open the server on | 9000
World| What worldfile to load. [See world files](https://github.com/DeltaF1/PySH/blob/master/docs/WorldFormat.md) | /world.json
Debug| Whether to create log files or not | false
