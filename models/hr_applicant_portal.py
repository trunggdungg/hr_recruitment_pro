# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrApplicantPortal(models.Model):
    _inherit = 'hr.applicant'

    recruiter_note = fields.Text(
        string='Ghi chú nhà tuyển dụng',
        help='Ghi chú riêng của nhà tuyển dụng về ứng viên này'
    )
    recruiter_feedback = fields.Selection([
        ('pending', 'Chờ xét duyệt'),
        ('interview', 'Mời phỏng vấn'),
        ('approved', 'Đạt yêu cầu'),
        ('contracted', 'Hợp đồng ký'),
        ('rejected', 'Fail'),
    ],
        string='Kết quả xét duyệt',
        default='pending',
        help='Kết quả xét duyệt của nhà tuyển dụng'
    )
    interview_date = fields.Datetime(
        string='Ngày phỏng vấn',
        help='Ngày hẹn phỏng vấn ứng viên'
    )
    interview_note = fields.Text(
        string='Ghi chú phỏng vấn',
        help='Ghi chú về buổi phỏng vấn'
    )
    interview_email_log = fields.Text(
        string='Lịch sử email mời phỏng vấn',
        default='[]',
        help='JSON log các lần gửi email mời phỏng vấn'
    )
    recruiter_partner_id = fields.Many2one(
        'res.partner',
        string='Nhà tuyển dụng',
        related='job_id.recruiter_id',
        readonly=True,
        store=False,
    )


    def portal_approve(self):
        """Duyệt ứng viên - chuyển sang phỏng vấn"""
        self.ensure_one()
        interview_stage = self.env['hr.recruitment.stage'].search([
            ('name', 'ilike', 'interview'),
            ('job_id', '=', False)
        ], limit=1) or self.env['hr.recruitment.stage'].search([], limit=1)
        
        self.write({
            'recruiter_feedback': 'interview',
            'stage_id': interview_stage.id if interview_stage else self.stage_id.id,
        })

    def portal_reject(self):
        """Từ chối ứng viên"""
        self.ensure_one()
        refused_stage = self.env['hr.recruitment.stage'].search([
            '|',
            ('name', 'ilike', 'refused'),
            ('name', 'ilike', 'reject'),
            ('job_id', '=', False)
        ], limit=1)
        
        self.write({
            'recruiter_feedback': 'rejected',
            'stage_id': refused_stage.id if refused_stage else self.stage_id.id,
        })

    def portal_mark_approved(self):
        """Đánh dấu ứng viên đạt yêu cầu"""
        self.ensure_one()
        self.write({
            'recruiter_feedback': 'approved',
        })

    def portal_mark_pending(self):
        """Đánh dấu chờ xét duyệt"""
        self.ensure_one()
        self.write({
            'recruiter_feedback': 'pending',
        })
