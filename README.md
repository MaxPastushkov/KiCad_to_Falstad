# Convert KiCad schematic files to Falstad text files [WORK IN PROGRESS]
The [Falstad circuit simulator applet](https://falstad.com/circuit/circuitjs.html) is a really nice and intuitive simulator, but unfortunately lacks any means to import schematics from any editors. This python script aims to solve that.

## Usage
`python kicad_to_falstad.py [filename].kicad_sch > falstad.txt`

Then in the simulator go to File -> Open File, and select `falstad.txt`

### This project is in a very early development stage, and could really use some help. Currently it only supports:
- Resistors
- Capacitors
- Diodes
- Inductors
- Transistors (BJTs, JFETs, MOSFETs)
