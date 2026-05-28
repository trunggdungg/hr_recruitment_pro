# -*- coding: utf-8 -*-

import logging
from odoo.exceptions import UserError
from odoo import models, fields, api
from datetime import date

_logger = logging.getLogger(__name__)


class HrJobInherit(models.Model):
    _inherit = 'hr.job'

    hr_job_photo = fields.Image(string='Ảnh Công Việc', attachment=True)
    is_portal_job = fields.Boolean(string='Job từ Portal', default=False, index=True)
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
    # NOTE: skill_ids is already defined in hr_skills module as computed from job_skill_ids
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



    # ========== Kiem duyet ==========
    moderation_state = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái duyệt', default='pending', tracking=True, copy=False)

    moderation_note = fields.Text(
        string='Ghi chú duyệt',
        help='Ghi chú của admin khi duyệt/từ chối bài'
    )
    moderation_date = fields.Datetime(
        string='Ngày duyệt',
        readonly=True,
        copy=False
    )
    moderator_id = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True,
        copy=False
    )

    def action_moderation_pending(self):
        """Chuyển sang trạng thái chờ duyệt (portal user submit)"""
        self.write({
            'moderation_state': 'pending',
            'moderation_note': False,
        })

    def action_moderation_approve(self, note=False):
        """Admin duyệt bài"""
        self.ensure_one()
        self.write({
            'moderation_state': 'approved',
            'moderation_date': fields.Datetime.now(),
            'moderator_id': self.env.user.id,
            'moderation_note': note or False,
            'website_published': True,  # Auto publish khi duyệt
        })
        self.message_post(
            body=f'Bài tuyển dụng đã được Admin duyệt và xuất bản.',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def action_moderation_reject(self, note=False):
        """Admin từ chối bài"""
        self.ensure_one()
        self.write({
            'moderation_state': 'rejected',
            'moderation_date': fields.Datetime.now(),
            'moderator_id': self.env.user.id,
            'moderation_note': note or False,
            'website_published': False,
        })
        self.message_post(
            body=f'Bài tuyển dụng đã bị từ chối. Lý do: {note or "Không có"}',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        for vals in vals_list:
            if 'moderation_state' not in vals:
                is_portal_job = vals.get('is_portal_job') or vals.get('recruiter_id')
                # Chỉ portal job mới cần duyệt
                vals['moderation_state'] = 'pending' if is_portal_job else 'approved'

            # Chỉ gán recruiter_id nếu là portal user thật (user.share=True)
            if not vals.get('recruiter_id') and user.share and user.partner_id.is_recruiter:
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

    def write(self, vals):
        # Chỉ chặn publish khi là portal job chưa duyệt
        if vals.get('website_published') is True:
            user = self.env.user
            if user.share:  # Chỉ chặn portal user, admin thì bỏ qua
                for job in self:
                    if job.recruiter_id and job.moderation_state != 'approved':
                        raise UserError(
                            f'Tin tuyển dụng "{job.name}" chưa được Admin duyệt. '
                            f'Không thể xuất bản.'
                        )

            # Job nội bộ admin → không chặn, cho publish tự do

        user = self.env.user
        if len(self) == 1:
            job = self
            content_fields = {
                'name', 'description', 'requirements', 'benefits',
                'salary_level_id', 'location_id', 'contract_type_id', 'degree_id',
                'experience_level', 'remote_policy', 'working_hours',
                'gender_require', 'age_require', 'trial_period', 'application_deadline',
                'no_of_recruitment',
            }
            is_content_edit = bool(content_fields & set(vals.keys()))

            if (user.share
                    and job.is_portal_job
                    and job.moderation_state in ['approved', 'rejected']
                    and user.partner_id.is_recruiter
                    and job.recruiter_id.id == user.partner_id.id
                    and is_content_edit):
                vals = {**vals, 'moderation_state': 'pending', 'website_published': False}

        return super().write(vals)

    def open_website_url(self):
        self.ensure_one()
        url = f'/recruitment/detail/{self.id}'
        _logger.info(">>> open_website_url called, redirecting to: %s", url)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',  # mở tab mới, đổi thành 'self' nếu muốn cùng tab
        }

    # Thêm vào class HrJobInherit trong models/hr_job.py

    def copy(self, default=None):
        default = default or {}
        if self.is_portal_job or self.recruiter_id:
            # Portal job → reset về pending, cần duyệt lại
            default.update({
                'moderation_state': 'pending',
                'website_published': False,
                'moderation_date': False,
                'moderator_id': False,
                'moderation_note': False,
            })
        else:
            # Job nội bộ → approved luôn, chỉ unpublish để admin tự quyết
            default.update({
                'moderation_state': 'approved',
                'website_published': False,
                'moderation_date': False,
                'moderator_id': False,
                'moderation_note': False,
            })
        return super().copy(default)