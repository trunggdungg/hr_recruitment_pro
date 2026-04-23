# -*- coding: utf-8 -*-

from odoo import models, fields


class HrRecruitmentLocation(models.Model):
    _name = 'hr.recruitment.location'
    _description = 'Địa Điểm Tuyển Dụng'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tên địa điểm',
        required=True,
        help='VD: Hà Nội, Hồ Chí Minh, Remote'
    )
    city = fields.Char(
        string='Thành phố',
        required=True,
        index=True,
        help='VD: Hà Nội, Hồ Chí Minh'
    )
    district = fields.Char(
        string='Quận/Huyện',
        help='VD: Quận 1, Đống Đa'
    )
    address = fields.Text(
        string='Địa chỉ chi tiết',
        help='VD: Tầng 10, Tòa nhà ABC, 123 Nguyễn Huệ'
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
        ('name_unique', 'unique(name)', 'Tên địa điểm đã tồn tại!'),
        ('city_name_unique', 'unique(city)', 'Thành phố đã tồn tại!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.district:
                name = f"{record.name} ({record.district})"
            result.append((record.id, name))
        return result
