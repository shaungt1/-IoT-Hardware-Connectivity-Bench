from scripts.dependency_inventory import license_text_identifier


def test_standard_license_text_identifiers() -> None:
    assert license_text_identifier("MIT License\n\nPermission is hereby granted, free of charge") == "MIT"
    assert license_text_identifier("Apache License\nVersion 2.0, January 2004") == "Apache-2.0"
    assert license_text_identifier(
        "Redistribution and use in source and binary forms are permitted. Neither the name may be used."
    ) == "BSD-3-Clause"
    assert license_text_identifier("Proprietary terms") is None
