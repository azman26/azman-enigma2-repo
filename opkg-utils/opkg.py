#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# opkg.py — finalna, poprawiona wersja z prawidłową obsługą formatu `ar`
#

import tarfile
import os
import arpy  # Nowa, wymagana biblioteka
import io    # Wymagane do obsługi danych w pamięci

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
        try:
            # KROK 1: Używamy biblioteki `arpy` do otwarcia zewnętrznego kontenera .ipk
            with arpy.Archive(filename) as archive:
                control_data = None
                
                # --- POCZĄTEK KLUCZOWEJ POPRAWKI ---
                # Zmieniamy sposób wyszukiwania pliku. Zamiast `startswith`, używamy `in`,
                # co jest bardziej elastyczne i znajdzie plik nawet jeśli jego nazwa
                # to np. './control.tar.gz'.
                for header in archive.headers:
                    if 'control.tar.gz' in header.name.decode():
                        control_data = archive.read(header)
                        break
                # --- KONIEC KLUCZOWEJ POPRAWKI ---

                if not control_data:
                    # Jeśli nadal nie znaleziono, wypiszmy nazwy plików, które tam są, dla diagnostyki
                    found_files = [h.name.decode() for h in archive.headers]
                    raise ValueError(f"Brak pliku 'control.tar.gz' w paczce. Znaleziono: {found_files}")

                # KROK 2: Tworzymy obiekt plikopodobny w pamięci z danych `control.tar.gz`
                control_fileobj = io.BytesIO(control_data)

                # KROK 3: Używamy `tarfile` do przetworzenia archiwum `control.tar.gz` z pamięci.
                with tarfile.open(fileobj=control_fileobj, mode="r:gz") as control_tar:
                    control_file_member = None
                    for member in control_tar.getmembers():
                        if member.name.endswith("control"):
                            control_file_member = member
                            break
                    
                    if not control_file_member:
                        raise ValueError("Brak pliku 'control' w archiwum control.tar.gz")

                    extracted_file = control_tar.extractfile(control_file_member)
                    if extracted_file:
                        control_content = extracted_file.read().decode("utf-8", errors="ignore")
                        self._parse_control_content(control_content)
                    else:
                        raise ValueError("Nie można wyodrębnić pliku 'control'")

        except Exception as e:
            raise ValueError(f"Błąd podczas parsowania pliku .ipk: {e}")

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