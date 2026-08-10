# -*- coding: utf-8 -*-

from odoo import models, fields


class HrRecruitmentLocation(models.Model):
    _name = 'hr.recruitment.location'
    _description = 'Địa Điểm Tuyển Dụng'
    _order = 'id'

    state_id = fields.Many2one(
        'res.country.state',
        string='Tỉnh/Thành phố',
        domain="[('country_id.code', '=', 'VN')]",
        required=True,
        index=True,
    )
    district = fields.Char(
        string='Quận/Huyện',
        index=True,
        help='VD: Quận 1, Đống Đa'
    )
    address = fields.Text(
        string='Địa chỉ chi tiết',
        help='VD: Tầng 10, Tòa nhà ABC, 123 Nguyễn Huệ'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        ('district_state_unique', 'unique(state_id, district)', 'Quận/Huyện đã tồn tại trong tỉnh/thành phố này!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = record.state_id.name or ''
            if record.district:
                name = f"{record.district}, {name}"
            result.append((record.id, name))
        return result
