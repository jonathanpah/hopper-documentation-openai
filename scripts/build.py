#!/usr/bin/env python3
"""Validate and package the two public plugins. Python 3.9+, standard library."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "pt-br")
PROGRAM = Path("skills/hopper-documentation-openai/scripts/hopper_documentation_openai.py")


def package_files(package):
    files = []
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if "__pycache__" in relative.parts or path.name == ".DS_Store":
            continue
        if path.is_symlink():
            raise ValueError("Package contains a symlink: " + str(relative))
        if not path.is_file():
            continue
        if path.suffix in (".pyc", ".pyo"):
            continue
        if path.name.startswith(".env") or path.suffix in (".key", ".p12", ".pfx"):
            raise ValueError("Package contains a credential candidate: " + str(relative))
        files.append((relative, path.read_bytes()))
    return files


def validate(files, package):
    for relative, data in files:
        if relative.suffix == ".py":
            compile(data, str(package / relative), "exec")
        elif relative.suffix == ".json":
            json.loads(data)
        elif relative.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", data.decode("utf-8")):
                target = target.split("#", 1)[0]
                if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                if not (package / relative.parent / target).exists():
                    raise ValueError("Broken local link: " + str(relative) + " -> " + target)


def python_payload(files, language):
    scripts = {name.as_posix(): data for name, data in files if name.suffix == ".py"}
    if set(scripts) != {PROGRAM.as_posix()}:
        raise ValueError("Package must contain only the version 2 Python program")
    lines = scripts[PROGRAM.as_posix()].splitlines(keepends=True)
    selectors = [line for line in lines if re.match(rb"^LANGUAGE\s*=", line)]
    pattern = rb"LANGUAGE[ \t]*=[ \t]*(['\"])" + language.encode("ascii") + rb"\1[ \t]*(?:\r?\n)?"
    if len(selectors) != 1 or not re.fullmatch(pattern, selectors[0]):
        raise ValueError("Invalid LANGUAGE selector for " + language)
    return b"".join(line for line in lines if line not in selectors)


def build(output, root=ROOT):
    prepared = []
    for language in LANGUAGES:
        package = root / ("hopper-documentation-openai-" + language)
        files = package_files(package)
        validate(files, package)
        manifest = json.loads((package / ".codex-plugin/plugin.json").read_text())
        if manifest["name"] != "hopper-documentation-openai":
            raise ValueError("Unexpected plugin identity")
        prepared.append((language, manifest["version"], files))
    if len({version for _, version, _ in prepared}) != 1:
        raise ValueError("Language package versions differ")
    # R36 permits only the LANGUAGE line to differ between the two programs.
    programs = [python_payload(files, language) for language, _, files in prepared]
    if programs[0] != programs[1]:
        raise ValueError("Python code differs beyond the LANGUAGE line")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sums = []
    for language, version, files in prepared:
        name = "hopper-documentation-openai-" + version + "-" + language + ".zip"
        target = output / name
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, data in files:
                entry = zipfile.ZipInfo(relative.as_posix(), (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
        sums.append(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + name)
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    return [line.split("  ", 1)[1] for line in sums]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "build")
    args = parser.parse_args()
    for name in build(args.out):
        print("Built " + str(args.out / name))
