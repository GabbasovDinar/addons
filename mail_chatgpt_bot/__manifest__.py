{
    "name": "Chat GPT Bot",
    "version": "16.0.1.0.0",
    "category": "Productivity/Discuss",
    "summary": "Add ChatGPT Bot in discussions",
    "depends": ["mail"],
    "auto_install": True,
    "installable": True,
    "data": [
        "data/res_partner.xml",
        "views/res_users_views.xml",
    ],
    "demo": [
        "data/mailbot_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_bot/static/src/scss/odoobot_style.scss",
        ],
    },
    "external_dependencies": {
        "python": [
            "openai",
        ],
    },
    "license": "LGPL-3",
}
