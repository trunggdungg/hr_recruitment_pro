# -*- coding: utf-8 -*-
{
    'name': 'Hr Recruitment Pro',
    'version': '1.0',
    'summary': 'Custom HR Recruitment with Salary and Location Filters',
    'description': '''
        Custom HR Recruitment module with salary level and location configuration and website filters.
    ''',
    'category': 'Recruitment',
    'author': 'Your Company',
    'company': '',
    'maintainer': '',
    'website': '',
    'depends': ['website_hr_recruitment'],
    'data': [
        'security/salary_security.xml',
        'security/location_security.xml',
        'security/ir.model.access.csv',

        'views/hr_recruitment_pro_web_views.xml',
        'views/hr_recruitment_salary_filter.xml',
        'views/hr_recruitment_location_filter.xml',
        'views/salary_inject_script.xml',
        'views/hr_job_form_views.xml',
        'views/hr_recruitment_salary_level_views.xml',
        'views/hr_recruitment_location_views.xml',
        'views/menu_views.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'hr_recruitment_pro/static/src/css/job_web_view.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
