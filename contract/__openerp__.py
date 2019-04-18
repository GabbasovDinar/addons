# -*- coding: utf-8 -*-
{
    "name": """contract""",
    "summary": """Contract Management""",
    "category": "Web",
    "images": [],
    "version": "1.0.0",
    "application": False,

    "author": "Dinar Gabbasov",
    "website": "https://twitter.com/gabbasov_dinar",
    "license": "LGPL-3",

    "depends": [
        "email_template",
    ],
    "external_dependencies": {"python": [], "bin": []},
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/contract_data.xml",
        "views/contract_view.xml",
    ],
    "demo": [],
    "qweb": [],

    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "uninstall_hook": None,

    "auto_install": False,
    "installable": True,
}
