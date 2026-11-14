"""Add BPMN interchange geometry to the transfer process source."""

from pathlib import Path
from xml.etree import ElementTree as ET

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DIAGRAM = "http://www.omg.org/spec/BPMN/20100524/DI"
BOUNDS = "http://www.omg.org/spec/DD/20100524/DC"
WAYPOINT = "http://www.omg.org/spec/DD/20100524/DI"
for prefix, namespace in (
    ("bpmn", BPMN),
    ("bpmndi", DIAGRAM),
    ("dc", BOUNDS),
    ("di", WAYPOINT),
):
    ET.register_namespace(prefix, namespace)

path = Path("docs/diagrams/transfer.bpmn")
root = ET.parse(path).getroot()
process = root.find(f"{{{BPMN}}}process")
assert process is not None
for prior in root.findall(f"{{{DIAGRAM}}}BPMNDiagram"):
    root.remove(prior)

diagram = ET.SubElement(root, f"{{{DIAGRAM}}}BPMNDiagram", id="TransferDiagram")
plane = ET.SubElement(
    diagram, f"{{{DIAGRAM}}}BPMNPlane", id="TransferPlane", bpmnElement="Transfer"
)
shapes = {
    "start": (50, 142, 36, 36),
    "auth": (120, 120, 150, 80),
    "auth_ok": (305, 135, 50, 50),
    "lock": (390, 120, 150, 80),
    "receipt": (575, 135, 50, 50),
    "replay": (655, 20, 150, 80),
    "check": (655, 120, 150, 80),
    "eligible": (840, 135, 50, 50),
    "reject": (925, 20, 150, 80),
    "post": (925, 120, 150, 80),
    "failure": (982, 182, 36, 36),
    "rollback": (925, 255, 150, 80),
    "done": (1155, 142, 36, 36),
}
for name, (x, y, width, height) in shapes.items():
    shape = ET.SubElement(
        plane, f"{{{DIAGRAM}}}BPMNShape", id=f"{name}_di", bpmnElement=name
    )
    ET.SubElement(
        shape,
        f"{{{BOUNDS}}}Bounds",
        x=str(x),
        y=str(y),
        width=str(width),
        height=str(height),
    )

detours = {
    ("auth_ok", "done"): [(330, 185), (330, 380), (1173, 380), (1173, 178)],
    ("receipt", "replay"): [(600, 135), (600, 60), (655, 60)],
    ("eligible", "reject"): [(865, 135), (865, 60), (925, 60)],
    ("replay", "done"): [(805, 60), (825, 60), (825, 8), (1173, 8), (1173, 142)],
    ("reject", "done"): [(1075, 60), (1173, 60), (1173, 142)],
    ("failure", "rollback"): [(1000, 218), (1000, 255)],
    ("rollback", "done"): [(1075, 295), (1173, 295), (1173, 178)],
}
for flow in process.findall(f"{{{BPMN}}}sequenceFlow"):
    source, target = flow.attrib["sourceRef"], flow.attrib["targetRef"]
    x, y, w, h = shapes[source]
    tx, ty, _, th = shapes[target]
    points = detours.get((source, target), [(x + w, y + h / 2), (tx, ty + th / 2)])
    edge = ET.SubElement(
        plane,
        f"{{{DIAGRAM}}}BPMNEdge",
        id=f"{flow.attrib['id']}_di",
        bpmnElement=flow.attrib["id"],
    )
    for px, py in points:
        ET.SubElement(edge, f"{{{WAYPOINT}}}waypoint", x=str(px), y=str(py))

ET.indent(root)
path.write_text(ET.tostring(root, encoding="unicode") + "\n")
