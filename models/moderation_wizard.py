# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ModerationWizard(models.TransientModel):
    """Wizard để duyệt/từ chối bài tuyển dụng với ghi chú"""
    _name = 'moderation.wizard'
    _description = 'Moderation Wizard'

    action = fields.Selection([
        ('approve', 'Duyệt đăng'),
        ('reject', 'Từ chối'),
        ('request_edit', 'Yêu cầu sửa lại'),
    ], string='Hành động', required=True)

    note = fields.Text(string='Ghi chú', placeholder='Nhập ghi chú cho nhà tuyển dụng...')

    @api.model
    def default_get(self, fields):
        """Lấy action mặc định từ context (được truyền từ button)"""
        res = super().default_get(fields)
        if self.env.context.get('default_action'):
            res['action'] = self.env.context.get('default_action')
        return res

    def action_apply(self):
        """Thực hiện hành động duyệt/từ chối"""
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])

        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}

        jobs = self.env['hr.job'].browse(active_ids)

        if self.action == 'approve':
            for job in jobs:
                job.action_moderation_approve(note=self.note)
            _logger.info('Approved %d jobs by user %s', len(jobs), self.env.user.name)

        elif self.action == 'reject':
            for job in jobs:
                job.action_moderation_reject(note=self.note)
            _logger.info('Rejected %d jobs by user %s', len(jobs), self.env.user.name)

        return {'type': 'ir.actions.act_window_close'}
