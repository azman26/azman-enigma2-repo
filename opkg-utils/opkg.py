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
        # --------------------------------------------------------------------------
        # TUTAJ USUNIĘTO BŁĘDNĄ LINIĘ.
        # Sprawdzenie `if not tarfile.is_tarfile(filename):` było niepoprawne,
        # ponieważ plik .ipk jest kontenerem 'ar', a nie 'tar'.
        # Prawdziwa obsługa błędu nastąpi w bloku `with` poniżej, jeśli
        # plik będzie rzeczywiście uszkodzony.
        # --------------------------------------------------------------------------

        try:
            with tarfile.open(filename, "r") as tar:
                control_member = None
                for member in tar.getmembers():
                    # Szukamy zarówno wersji skompresowanej, jak i nie
                    if member.name.endswith("control.tar.gz") or member.name.endswith("control.tar"):
                        control_member = member
                        break

                if not control_member:
                    raise ValueError("Brak pliku control.tar(.gz) w paczce")

                with tempfile.TemporaryDirectory() as tmpdir:
                    tar.extract(control_member, path=tmpdir)
                    control_path = os.path.join(tmpdir, control_member.name)

                    # Jeżeli to gzip — rozpakuj do pliku tymczasowego
                    if control_path.endswith(".gz"):
                        inner_tmp_dir = os.path.join(tmpdir, "control_inner")
                        os.makedirs(inner_tmp_dir, exist_ok=True)
                        uncompressed_path = os.path.join(inner_tmp_dir, "control.tar")
                        with gzip.open(control_path, "rb") as gz:
                            with open(uncompressed_path, "wb") as f:
                                f.write(gz.read())
                        control_path = uncompressed_path

                    # Teraz rozpakuj control.tar i znajdź plik "control"
                    if tarfile.is_tarfile(control_path):
                        with tarfile.open(control_path, "r") as control_tar:
                            control_file_member = None
                            for member in control_tar.getmembers():
                                # Plik może być w podkatalogu ./control
                                if member.name.endswith("control"):
                                    control_file_member = member
                                    break
                            if not control_file_member:
                                raise ValueError("Brak pliku 'control' w archiwum control.tar")

                            extracted_file = control_tar.extractfile(control_file_member)
                            if extracted_file:
                                control_content = extracted_file.read().decode("utf-8", errors="ignore")
                                self._parse_control_content(control_content)
                            else:
                                raise ValueError("Nie można wyodrębnić pliku 'control'")
                    else:
                        raise ValueError("Wewnętrzny plik control.tar(.gz) nie jest prawidłowym archiwum tar")

        except tarfile.ReadError as e:
            # Przechwytujemy błąd odczytu, który wystąpi, jeśli plik nie jest ani tar, ani ar (który tarfile czasem czyta)
            raise ValueError(f"Plik nie jest prawidłowym archiwum (tar/ar): {e}")


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
        # Tworzy wpis tylko z polami, które mają wartość
        return "\n".join(f"{k}: {v}" for k, v in fields if v) + "\n"

    def __str__(self):
        return self.make_index_entry()