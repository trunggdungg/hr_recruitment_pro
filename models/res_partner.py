# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_recruiter = fields.Boolean(
        string='Là nhà tuyển dụng',
        default=False,
        help='Khi bật, partner này sẽ có quyền đăng tin tuyển dụng trên portal'
    )

    recruiter_verified = fields.Boolean(string='Đã xác minh', default=False)

    # Liên kết đến jobs đã đăng (job.recruiter_id = partner này)
    recruiter_job_ids = fields.One2many(
        'hr.job',
        'recruiter_id',
        string='Việc làm đã đăng'
    )
    recruiter_job_count = fields.Integer(
        string='Số tin tuyển dụng',
        compute='_compute_recruiter_job_count',
    )

    @api.depends('recruiter_job_ids')
    def _compute_recruiter_job_count(self):
        for partner in self:
            partner.recruiter_job_count = len(partner.recruiter_job_ids)

    @api.constrains('email')
    def _check_unique_email(self):
        for partner in self:
            if not partner.email:
                continue

            email = partner.email.strip().lower()

            duplicate = self.search([
                ('id', '!=', partner.id),
                ('email', '=ilike', email),
            ], limit=1)

            if duplicate:
                raise ValidationError(_(
                    "Email '%s' đã tồn tại trên contact '%s'. "
                    "Vui lòng sử dụng email khác."
                ) % (partner.email, duplicate.display_name))