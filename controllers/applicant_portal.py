# -*- coding: utf-8 -*-
import logging
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


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
        """Xử lý các action xét duyệt"""
        applicant = request.env['hr.applicant'].browse(applicant_id)
        
        if not applicant.exists():
            return {'error': 'Applicant not found'}
        
        # Kiểm tra quyền
        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return {'error': 'Permission denied'}
        
        note = kwargs.get('note', '')
        interview_date = kwargs.get('interview_date')
        
        try:
            if action == 'approve':
                # Duyệt - chuyển sang phỏng vấn
                interview_stage = request.env['hr.recruitment.stage'].search([
                    ('name', 'ilike', 'interview')
                ], limit=1)
                
                vals = {
                    'recruiter_feedback': 'interview',
                }
                if interview_stage:
                    vals['stage_id'] = interview_stage.id
                if note:
                    vals['recruiter_note'] = note
                if interview_date:
                    vals['interview_date'] = interview_date
                    
                applicant.write(vals)
                message = 'Đã chuyển sang danh sách phỏng vấn'
                
            elif action == 'reject':
                # Từ chối
                refused_stage = request.env['hr.recruitment.stage'].search([
                    '|',
                    ('name', 'ilike', 'refused'),
                    ('name', 'ilike', 'reject')
                ], limit=1)
                
                vals = {
                    'recruiter_feedback': 'rejected',
                }
                if refused_stage:
                    vals['stage_id'] = refused_stage.id
                if note:
                    vals['recruiter_note'] = note
                    
                applicant.write(vals)
                message = 'Đã từ chối ứng viên'
                
            elif action == 'mark_approved':
                # Đánh dấu đạt (không đổi stage)
                applicant.write({
                    'recruiter_feedback': 'approved',
                    'recruiter_note': note or applicant.recruiter_note,
                })
                message = 'Đã đánh dấu ứng viên đạt yêu cầu'
                
            elif action == 'mark_pending':
                # Đánh dấu chờ xét duyệt
                applicant.write({
                    'recruiter_feedback': 'pending',
                    'recruiter_note': note or applicant.recruiter_note,
                })
                message = 'Đã đánh dấu chờ xét duyệt'
                
            elif action == 'update_note':
                # Chỉ cập nhật ghi chú
                applicant.write({
                    'recruiter_note': note,
                })
                message = 'Đã cập nhật ghi chú'
                
            else:
                return {'error': f'Unknown action: {action}'}
            
            _logger.info('Applicant %s action: %s by user %s', applicant_id, action, user.id)
            return {'success': True, 'message': message}
            
        except Exception as e:
            _logger.error('Error processing applicant action: %s', str(e))
            return {'error': str(e)}

    @route('/my/recruitment/applicant/<int:applicant_id>/schedule_interview',
           type='http', auth='user', website=True, csrf=False)
    def portal_schedule_interview(self, applicant_id, **post):
        """Hẹn lịch phỏng vấn"""
        applicant = request.env['hr.applicant'].browse(applicant_id)
        
        if not applicant.exists():
            return request.redirect('/my/recruitment?tab=applicants')
        
        # Kiểm tra quyền
        user = request.env.user
        if applicant.job_id.user_id.id != user.id:
            return request.redirect('/my/recruitment?tab=applicants')
        
        interview_date = post.get('interview_date')
        interview_note = post.get('interview_note', '')
        
        if interview_date:
            applicant.write({
                'interview_date': interview_date,
                'interview_note': interview_note,
                'recruiter_feedback': 'interview',
            })
            
            # Chuyển sang stage phỏng vấn
            interview_stage = request.env['hr.recruitment.stage'].search([
                ('name', 'ilike', 'interview')
            ], limit=1)
            if interview_stage:
                applicant.stage_id = interview_stage
        
        return request.redirect(f'/my/recruitment/applicant/{applicant_id}')
