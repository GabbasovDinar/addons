{
    "name": "Contact Deduplication",
    "version": "12.0.1.0.0",
    "summary": "Contact Deduplicate Extension",
    "author": "Dinar Gabbasov",
    "license": "LGPL-3",
    "category": "Technical",
    "website": "https://www.linkedin.com/in/dinar-gabbasov/",
    "description": """
Contact Deduplicate Extension
=============================
    """,
    "depends": ["contacts"],
    "data": [
        "wizards/base_partner_merge_automatic_wizard_view.xml",
    ],
    "qweb": [],
    "installable": True,
    "application": False,
    "external_dependencies": {
        "python": ["thefuzz"],
    },
}
