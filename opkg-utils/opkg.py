#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# opkg.py — minimalna wersja z pominięciem Size/Installed-Size
# oraz obsługą brakujących pól w .ipk
#

import tarfile
import tempfile
import os

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
                if control_path.endswith(".gz"):
                    import gzip
                    with gzip.open(control_path, "rb") as gz:
                        self._parse_control_content(gz.read().decode("utf-8", errors="ignore"))
                else:
                    with open(control_path, "r", encoding="utf-8", errors="ignore") as f:
                        self._parse_control_content(f.read())

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
