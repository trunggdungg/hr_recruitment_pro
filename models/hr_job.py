# -*- coding: utf-8 -*-

from odoo import models, fields


class HrJobInherit(models.Model):
    _inherit = 'hr.job'

    salary_level_id = fields.Many2one(
        'hr.recruitment.salary.level',
        string='Mức Lương',
        tracking=True,
        help='Chọn mức lương cho vị trí tuyển dụng'
    )
    location_id = fields.Many2one(
        'hr.recruitment.location',
        string='Địa Điểm',
        tracking=True,
        help='Chọn địa điểm làm việc'
    )
