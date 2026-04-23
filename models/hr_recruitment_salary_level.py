# -*- coding: utf-8 -*-

from odoo import models, fields


class HrRecruitmentSalaryLevel(models.Model):
    _name = 'hr.recruitment.salary.level'
    _description = 'Mức Lương Tuyển Dụng'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tên mức lương',
        required=True,
        help='VD: Dưới 10 triệu, 10-20 triệu'
    )
    min_salary = fields.Integer(
        string='Lương tối thiểu (VND)',
        required=True,
        default=0,
        help='Lương tối thiểu của mức này (VND)'
    )
    max_salary = fields.Integer(
        string='Lương tối đa (VND)',
        required=True,
        default=0,
        help='Lương tối đa của mức này (VND). Đặt 0 nếu không giới hạn.'
    )
    sequence = fields.Integer(
        string='Thứ tự',
        default=10,
        help='Thứ tự hiển thị'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Cho phép sử dụng'
    )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tên mức lương đã tồn tại!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            if record.max_salary == 0:
                name = f"{record.name} ({record.min_salary:,.0f}+ VND)"
            else:
                name = f"{record.name} ({record.min_salary:,.0f} - {record.max_salary:,.0f} VND)"
            result.append((record.id, name))
        return result
