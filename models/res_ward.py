# -*- coding: utf-8 -*-
from odoo import models, fields

class ResWard(models.Model):
    _name = 'res.ward'
    _description = 'Phường/Xã'
    _order = 'name'

    name = fields.Char(string='Tên phường/xã', required=True)
    state_id = fields.Many2one(
        'res.country.state',
        string='Tỉnh/Thành phố',
        required=True,
        ondelete='cascade',
        index=True,
    )