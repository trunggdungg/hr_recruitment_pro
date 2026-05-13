# -*- coding: utf-8 -*-
import logging
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)
FEEDBACK_TO_KANBAN = {
        'pending': 'normal',
        'interview': 'done',
        'approved': 'done',
        'contracted': 'done',
        'rejected': 'blocked',
    }

class ApplicantPortal(CustomerPortal):


    def _get_applicant_domain(self):
        """Lấy domain để lọc ứng viên thuộc jobs của recruiter hiện tại"""
        user = request.env.user
        return [
            ('job_id.user_id', '=', user.id)
        ]

    @route('/my/recruitment/applicant/<int:applicant_id>', 
           type='http', auth='user', website=True)
    def portal_applicant_detail(self, applicant_id, **kwargs):
        """Trang chi tiết ứng viên"""
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
        
        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')
        
        # Kiểm tra quyền: chỉ recruiter sở hữu job mới được xem
        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            _logger.warning('User %s attempted to access applicant %s without permission', 
                          user.id, applicant_id)
            return request.redirect('/my/recruitment?tab=applicants')
        
        # Lấy danh sách stages để hiển thị (tất cả stages)
        stages = request.env['hr.recruitment.stage'].sudo().search([], order='sequence asc')
        
        values = {
            'applicant': applicant,
            'stages': stages,
            'page_name': 'applicant_detail',
            'redirect_url': '/my/recruitment?tab=applicants',
        }
        
        return request.render('hr_recruitment_pro.portal_applicant_detail', values)

    @route('/my/recruitment/applicant/<int:applicant_id>/action',
           type='json', auth='user', website=True)
    def portal_applicant_action(self, applicant_id, action, **kwargs):
        """Xử lý chuyển trạng thái - không cần note"""
        applicant = request.env['hr.applicant'].browse(applicant_id)

        if not applicant.exists():
            return {'error': 'Applicant not found'}

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return {'error': 'Permission denied'}

        VALID_ACTIONS = {
            'pending': ('pending', 'Chuyển về Chờ xét duyệt'),
            'interview': ('interview', 'Đã chuyển sang Mời phỏng vấn'),
            'approved': ('approved', 'Đã đánh dấu Đạt yêu cầu'),
            'contracted': ('contracted', 'Đã xác nhận Hợp đồng ký'),
            'rejected': ('rejected', 'Đã đánh dấu Fail'),
        }

        if action not in VALID_ACTIONS:
            return {'error': f'Unknown action: {action}'}

        try:
            feedback_value, message = VALID_ACTIONS[action]
            applicant.write({
                'recruiter_feedback': feedback_value,
                'kanban_state': FEEDBACK_TO_KANBAN.get(feedback_value, 'normal'),
            })
            _logger.info('Applicant %s → %s by user %s', applicant_id, feedback_value, user.id)
            return {'success': True, 'message': message}

        except Exception as e:
            _logger.error('Error processing applicant action: %s', str(e))
            return {'error': str(e)}

    @route('/my/recruitment/applicant/<int:applicant_id>/update_note',
           type='http', auth='user', website=True, csrf=True)
    def portal_update_note(self, applicant_id, **post):
        """Cập nhật ghi chú nhà tuyển dụng"""
        _logger.info('===== START: portal_update_note =====')
        _logger.info('applicant_id: %s', applicant_id)
        _logger.info('POST data: %s', post)
        _logger.info('User: %s (id=%s)', request.env.user.name, request.env.user.id)

        applicant = request.env['hr.applicant'].browse(applicant_id)

        if not applicant.exists():
            _logger.warning('Applicant %s does not exist', applicant_id)
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            _logger.warning('User %s has no permission to update applicant %s', user.id, applicant_id)
            return request.redirect('/my/recruitment?tab=applicants')

        note = post.get('note', '')
        _logger.info('Note content length: %s', len(note))
        _logger.info('Note preview (first 100 chars): %s', note[:100] if note else 'EMPTY')

        try:
            applicant.write({'recruiter_note': note})
            _logger.info('SUCCESS: Updated recruiter_note for applicant %s', applicant_id)
            _logger.info('Verify - New note in DB: %s', applicant.recruiter_note[:100] if applicant.recruiter_note else 'EMPTY')
        except Exception as e:
            _logger.error('ERROR updating note for applicant %s: %s', applicant_id, str(e), exc_info=True)

        _logger.info('===== END: portal_update_note =====')
        return request.redirect(f'/my/recruitment/applicant/{applicant_id}')

    @route('/my/recruitment/applicant/<int:applicant_id>/schedule_interview',
           type='http', auth='user', website=True, csrf=True)
    def portal_schedule_interview(self, applicant_id, **post):
        """Hẹn lịch phỏng vấn"""
        applicant = request.env['hr.applicant'].browse(applicant_id)

        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')

        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=applicants')

        interview_date = post.get('interview_date')
        interview_note = post.get('interview_note', '')

        if interview_date:
            applicant.write({
                'interview_date': interview_date,
                'interview_note': interview_note,
                # KHÔNG đổi stage_id, KHÔNG đổi recruiter_feedback
            })

        return request.redirect(f'/my/recruitment/applicant/{applicant_id}')