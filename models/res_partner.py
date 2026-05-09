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

    # Thông tin công ty tuyển dụng
    # recruiter_company_name = fields.Char(
    #     string='Tên công ty',
    #     help='Tên công ty hiển thị trên tin tuyển dụng'
    # )
    # recruiter_company_logo = fields.Binary(
    #     string='Logo công ty',
    #     attachment=True
    # )
    # recruiter_tax_id = fields.Char(
    #     string='Mã số thuế'
    # )
    # recruiter_company_size = fields.Selection([
    #     ('1_10', '1-10 người'),
    #     ('10_50', '10-50 người'),
    #     ('50_200', '50-200 người'),
    #     ('200_500', '200-500 người'),
    #     ('500+', '500+ người'),
    # ], string='Quy mô công ty')
    # recruiter_industry = fields.Char(string='Ngành nghề')
    recruiter_verified = fields.Boolean(string='Đã xác minh', default=False)
    # recruiter_description = fields.Text(string='Giới thiệu công ty')

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
