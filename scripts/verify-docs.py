import re
from pathlib import Path
from xml.etree import ElementTree

root = Path(__file__).resolve().parents[1]
for document in root.rglob("*.md"):
    if any(
        part.startswith(".") or part in {"node_modules", "dist"}
        for part in document.relative_to(root).parts
    ):
        continue
    for destination in re.findall(r"\]\(([^)]+)\)", document.read_text()):
        path = destination.split("#")[0]
        if path and not path.startswith(("http://", "https://", "mailto:")):
            if not (document.parent / path).exists():
                raise SystemExit(
                    f"Broken link in {document.relative_to(root)}: {destination}"
                )
bpmn = ElementTree.parse(root / "docs/diagrams/transfer.bpmn")
ids = set()
for node in bpmn.iter():
    identifier = node.get("id")
    if identifier is None:
        continue
    if identifier in ids:
        raise SystemExit(f"Duplicate BPMN ID: {identifier}")
    ids.add(identifier)
for node in bpmn.iter():
    for attribute in ("sourceRef", "targetRef", "attachedToRef", "bpmnElement"):
        if attribute in node.attrib and node.get(attribute) not in ids:
            raise SystemExit(f"Invalid BPMN reference: {node.attrib[attribute]}")
