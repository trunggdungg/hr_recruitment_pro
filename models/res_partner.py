# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_recruiter = fields.Boolean(
        string='Là nhà tuyển dụng',
        default=False,
        help='Khi bật, partner này sẽ có quyền đăng tin tuyển dụng trên portal'
    )

    recruiter_verified = fields.Boolean(string='Đã xác minh', default=False)

    # Liên kết đến jobs đã đăng
    recruiter_job_ids = fields.One2many(
        'hr.job',
        compute='_compute_recruiter_jobs',
        string='Việc làm đã đăng'
    )
    recruiter_job_count = fields.Integer(
        string='Số tin tuyển dụng',
        compute='_compute_recruiter_jobs',
    )

    @api.depends('user_ids')
    def _compute_recruiter_jobs(self):
        for partner in self:
            # Tìm user liên kết với partner này
            users = self.env['res.users'].search([('partner_id', '=', partner.id)])
            if users:
                jobs = self.env['hr.job'].search([('user_id', 'in', users.ids)])
            else:
                jobs = self.env['hr.job']
            partner.recruiter_job_ids = jobs
            partner.recruiter_job_count = len(jobs)
