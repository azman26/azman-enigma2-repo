#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# opkg.py — poprawiona wersja
# Obsługuje .ipk niezależnie od struktury archiwum,
# pomija Size/Installed-Size, nie wywala błędów na brakujących polach.
#

import tarfile
import tempfile
import os
import gzip

class Package:
    def __init__(self, filename):
        self.filename = filename
        self.package = None
        self.version = None
        self.architecture = None
        self.description = None
        self.maintainer = None
        self.depends = None
        self.priority = None
        self.section = None

        self._parse_ipk(filename)

    def _parse_ipk(self, filename):
        if not tarfile.is_tarfile(filename):
            raise ValueError("Plik nie jest archiwum tar")

        with tarfile.open(filename, "r") as tar:
            control_member = None
            for member in tar.getmembers():
                if member.name.endswith("control.tar.gz") or member.name.endswith("control.tar"):
                    control_member = member
                    break

            if not control_member:
                raise ValueError("Brak pliku control.tar(.gz) w paczce")

            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extract(control_member, path=tmpdir)
                control_path = os.path.join(tmpdir, control_member.name)

                # Jeżeli to gzip — rozpakuj
                if control_path.endswith(".gz"):
                    inner_tmp = os.path.join(tmpdir, "control_inner")
                    os.makedirs(inner_tmp, exist_ok=True)
                    with gzip.open(control_path, "rb") as gz:
                        with open(os.path.join(inner_tmp, "control.tar"), "wb") as f:
                            f.write(gz.read())
                    control_path = os.path.join(inner_tmp, "control.tar")

                # Teraz rozpakuj control.tar i znajdź plik "control"
                if tarfile.is_tarfile(control_path):
                    with tarfile.open(control_path, "r") as control_tar:
                        control_file = None
                        for member in control_tar.getmembers():
                            if member.name == "control":
                                control_file = member
                                break
                        if not control_file:
                            raise ValueError("Brak pliku 'control' w control.tar")

                        control_content = control_tar.extractfile(control_file).read().decode("utf-8", errors="ignore")
                        self._parse_control_content(control_content)
                else:
                    raise ValueError("control.tar(.gz) nie jest prawidłowym archiwum")

    def _parse_control_content(self, content):
        for line in content.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key.lower() == "package":
                self.package = value
            elif key.lower() == "version":
                self.version = value
            elif key.lower() == "architecture":
                self.architecture = value
            elif key.lower() == "description":
                self.description = value
            elif key.lower() == "maintainer":
                self.maintainer = value
            elif key.lower() == "depends":
                self.depends = value
            elif key.lower() == "priority":
                self.priority = value
            elif key.lower() == "section":
                self.section = value

    def make_index_entry(self):
        """Tworzy wpis w pliku Packages bez Size i Installed-Size"""
        fields = [
            ("Package", self.package),
            ("Version", self.version),
            ("Architecture", self.architecture),
            ("Maintainer", self.maintainer),
            ("Depends", self.depends),
            ("Priority", self.priority),
            ("Section", self.section),
            ("Description", self.description),
            ("Filename", os.path.basename(self.filename)),
        ]
        return "\n".join(f"{k}: {v}" for k, v in fields if v) + "\n"

    def __str__(self):
        return self.make_index_entry()
