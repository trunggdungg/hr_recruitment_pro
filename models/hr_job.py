# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from datetime import date

_logger = logging.getLogger(__name__)
class HrJobInherit(models.Model):
    _inherit = 'hr.job'

    recruiter_id = fields.Many2one(
        'res.partner',
        string='Nhà tuyển dụng',
        index=True,
        ondelete='cascade',
        help='Partner đã đăng tin tuyển dụng này'
    )
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
    contract_type_id = fields.Many2one(
        'hr.contract.type',
        string='Loại công việc',
        tracking=True,
    )
    degree_id = fields.Many2one(
        'hr.recruitment.degree',
        string='Trình độ yêu cầu',
        tracking=True,
        help='Trình độ học vấn yêu cầu cho vị trí này'
    )
    job_skills = fields.Text(
        string='Kỹ năng mong đợi',
        help='Các kỹ năng mong đợi từ ứng viên'
    )
    requirements = fields.Html(
        string='Yêu cầu ứng viên',
        sanitize=True,  # ← đổi thành True
        sanitize_style=True,  # ← cho phép giữ inline style
    )
    benefits = fields.Html(
        string='Quyền lợi',
        sanitize=True,
        sanitize_style=True,
    )
    description = fields.Html(
        string='Mô tả công việc',
        sanitize=True,
        sanitize_style=True,
    )
    working_hours = fields.Char(
        string='Giờ làm việc',
        help='VD: Thứ 2 - Thứ 6, 8h00 - 17h00'
    )
    experience_level = fields.Selection([
        ('intern', 'Thực tập'),
        ('fresher', 'Mới tốt nghiệp'),
        ('junior', 'Junior (1-2 năm)'),
        ('mid', 'Mid-level (3-5 năm)'),
        ('senior', 'Senior (5+ năm)'),
        ('lead', 'Lead / Quản lý'),
    ], string='Cấp bậc kinh nghiệm', default='mid')
    remote_policy = fields.Selection([
        ('onsite', 'Tại văn phòng'),
        ('hybrid', 'Hybrid (Kết hợp)'),
        ('remote', 'Remote (Từ xa)'),
    ], string='Chính sách làm việc', default='onsite')
    gender_require = fields.Selection([
        ('both', 'Không giới hạn'),
        ('male', 'Nam'),
        ('female', 'Nữ'),
    ], string='Yêu cầu giới tính', default='both')
    age_require = fields.Char(
        string='Yêu cầu độ tuổi',
        help='VD: 22-35 tuổi'
    )
    trial_period = fields.Integer(
        string='Thời gian thử việc (tháng)',
        default=2
    )
    application_deadline = fields.Date(
        string='Hạn nộp hồ sơ',
        help='Ngày kết thúc nhận hồ sơ ứng tuyển',
        tracking=True,
    )
    probation_salary_ratio = fields.Integer(
        string='Lương thử việc (%)',
        default=85,
        help='Tỷ lệ lương thử việc so với lương chính thức'
    )

    # is_portal_job = fields.Boolean(
    #     string='Bài đăng từ Portal',
    #     default=False,
    #     help='True nếu bài được đăng bởi nhà tuyển dụng qua portal'
    # )
    #
    # # Thêm field source_type để hiển thị text đẹp hơn
    # source_type = fields.Selection([
    #     ('portal', 'Nhà tuyển dụng'),
    #     ('admin', 'Nội bộ'),
    # ], string='Nguồn đăng', compute='_compute_source_type', store=False)
    #
    # def _compute_source_type(self):
    #     for job in self:
    #         job.source_type = 'portal' if job.is_portal_job else 'admin'

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động gán recruiter_id nếu user là recruiter"""
        user = self.env.user
        for vals in vals_list:
            if not vals.get('recruiter_id'):
                if user.partner_id.is_recruiter:
                    vals['recruiter_id'] = user.partner_id.id
        return super().create(vals_list)

    def _cron_auto_unpublish_expired_jobs(self):
        """Cron: Tự động gỡ bài đăng khi hết hạn"""
        today = date.today()
        # Tìm các job đang được đăng, có hạn chót, và đã hết hạn
        expired_jobs = self.search([
            ('website_published', '=', True),
            ('application_deadline', '!=', False),
            ('application_deadline', '<', today),
            ('active', '=', True),
        ])
        for job in expired_jobs:
            job.write({'website_published': False})
            job.message_post(
                body=f'Tin tuyển dụng đã tự động gỡ do hết hạn vào ngày {job.application_deadline.strftime("%d/%m/%Y")}.',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def open_website_url(self):
        self.ensure_one()
        url = f'/recruitment/detail/{self.id}'
        _logger.info(">>> open_website_url called, redirecting to: %s", url)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',  # mở tab mới, đổi thành 'self' nếu muốn cùng tab
        }