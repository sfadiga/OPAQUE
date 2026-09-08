# Translations

The source language of the OPAQUE framework is English. This directory holds
the compiled `.qm` files that `opaque.localisation.install_translator` loads at
start up. A missing file is normal: the framework then shows English.

## Add a language

Run both commands from the repository root. Replace `pt_BR` with the locale you
want.

1. Collect every string from the source into a `.ts` file:

```
venv\Scripts\pyside6-lupdate.exe src/opaque -ts src/opaque/translations/opaque_pt_BR.ts
```

2. Translate the `.ts` file. `venv\Scripts\pyside6-linguist.exe` opens it.

3. Compile the `.ts` file into the `.qm` file the application loads:

```
venv\Scripts\pyside6-lrelease.exe src/opaque/translations/opaque_pt_BR.ts -qm src/opaque/translations/opaque_pt_BR.qm
```

## Rules

- `lupdate` reads the **source text** of a `tr()` call. `tr(variable)` and
  `tr(f"...")` produce nothing. `tests/test_localisation.py` fails the build
  when either appears.
- Commit the `.ts` file. Commit the `.qm` file too, so a user does not need
  the Qt tools to run the application.
- A translated string is often 30 to 40 per cent longer than the English
  source. Never give a container that holds a translated string a fixed size.
